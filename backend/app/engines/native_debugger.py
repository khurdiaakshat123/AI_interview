"""Native debugger adapters. Execution and serialization reuse the Run harnesses."""
import ast
from collections import deque
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time

import psutil
import websocket

from backend.app.engines.c_runner import CRunner
from backend.app.engines.sandbox_runner import SandboxRunner, ToolchainUnavailableError


def result(status, steps=None, error=None, value=None, stdout=""):
    steps = steps or []
    return dict(status=status, steps=steps, total_steps=len(steps), error=error,
                return_value=value, stdout=stdout, max_steps_reached=status == "STEP_LIMIT")


def kill_tree(proc):
    try:
        parent = psutil.Process(proc.pid)
        children = parent.children(recursive=True)
        for child in reversed(children):
            try:
                child.kill()
            except psutil.Error:
                pass
        parent.kill()
        psutil.wait_procs(children + [parent], timeout=2)
    except psutil.Error:
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)
    for reader in getattr(proc, "_debug_readers", []):
        reader.join(timeout=2)
    for stream in (proc.stdin, proc.stdout, proc.stderr):
        if stream and not stream.closed:
            try:
                stream.close()
            except OSError:
                pass


def read(path):
    return Path(path).read_text(encoding="utf-8", errors="replace") if Path(path).exists() else ""


def payload_row(output):
    start = output.rfind("---SANDBOX_RESULTS_START---")
    end = output.rfind("---SANDBOX_RESULTS_END---")
    if start < 0 or end < start:
        raise ValueError("Program did not complete its execution harness")
    rows = json.loads(output[start + len("---SANDBOX_RESULTS_START---"):end])["results"]
    if len(rows) != 1:
        raise ValueError("Debugger expected exactly one execution result")
    return rows[0]


def completed(steps, row, stdout=""):
    actual = row["actual_output"]
    if str(actual).startswith(("Runtime Error:", "Runtime Exception", "No solution", "Design class not found")):
        return result("RUNTIME_ERROR", steps, str(actual), stdout=stdout or row.get("stdout", ""))
    return result("SUCCESS", steps, value=decode_value(actual), stdout=stdout or row.get("stdout", ""))


def decode_value(value):
    try:
        return json.loads(value) if isinstance(value, str) else value
    except ValueError:
        return value


def mi_fields(text):
    """Parse GDB/MI tuples and lists without splitting quoted commas/braces."""
    pos = 0

    def value():
        nonlocal pos
        if text[pos] == '"':
            start = pos
            pos += 1
            while pos < len(text):
                if text[pos] == "\\":
                    pos += 2
                elif text[pos] == '"':
                    pos += 1
                    break
                else:
                    pos += 1
            return ast.literal_eval(text[start:pos])
        if text[pos] == "{":
            pos += 1
            val = fields("}")
            pos += 1
            return val
        if text[pos] == "[":
            pos += 1
            items = []
            while pos < len(text) and text[pos] != "]":
                match = re.match(r"[\w-]+=", text[pos:])
                if match:
                    key = match.group()[:-1]
                    pos += len(match.group())
                    items.append({key: value()})
                else:
                    items.append(value())
                if pos < len(text) and text[pos] == ",":
                    pos += 1
            pos += 1
            return items
        start = pos
        while pos < len(text) and text[pos] not in ",}]":
            pos += 1
        return text[start:pos]

    def fields(end=""):
        nonlocal pos
        out = {}
        while pos < len(text) and (not end or text[pos] != end):
            match = re.match(r"([\w-]+)=", text[pos:])
            if not match:
                raise ValueError("Invalid GDB/MI field")
            pos += len(match.group())
            out[match[1]] = value()
            if pos < len(text) and text[pos] == ",":
                pos += 1
            else:
                break
        return out

    return fields()


class MI:
    def __init__(self, gdb, cwd, deadline):
        self.proc = subprocess.Popen([gdb, "--quiet", "--interpreter=mi2"], cwd=cwd,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace", bufsize=1)
        self.lines = queue.Queue()
        self.events = deque()
        self.deadline, self.token = deadline, 0
        def pump():
            for line in self.proc.stdout:
                self.lines.put(line.strip())
            self.lines.put(None)
        reader = threading.Thread(target=pump, daemon=True)
        self.proc._debug_readers = [reader]
        reader.start()

    def line(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Native debugger timed out")
        try:
            line = self.lines.get(timeout=remaining)
        except queue.Empty as exc:
            raise TimeoutError("Native debugger timed out") from exc
        if line is None:
            raise RuntimeError("GDB exited before program completion")
        return line

    def command(self, command, optional=False):
        self.token += 1
        token = str(self.token)
        self.proc.stdin.write(token + command + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.line()
            if line.startswith("*stopped"):
                self.events.append(mi_fields(line.partition(",")[2]))
            if line.startswith(token + "^"):
                state, _, fields = line[len(token) + 1:].partition(",")
                data = mi_fields(fields) if fields else {}
                if state == "error" and not optional:
                    raise RuntimeError(data.get("msg", "GDB command failed"))
                return data

    def stopped(self):
        while not self.events:
            line = self.line()
            if line.startswith("*stopped"):
                self.events.append(mi_fields(line.partition(",")[2]))
        return self.events.popleft()


def trace_gdb(code, language, input_data, max_steps, timeout):
    compiler = shutil.which("gcc" if language == "c" else "g++")
    gdb = shutil.which("gdb")
    if not compiler or not gdb:
        return result("TOOLCHAIN_UNAVAILABLE", error="Native compiler and GDB are required.")
    sig = CRunner.detect_c_signature(code) if language == "c" else SandboxRunner._detect_cpp_signature(code)
    if not sig:
        return result("COMPILATION_ERROR", error="Could not identify the solution function.")
    ret, method, params = sig
    steps, session = [], None
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        ext = "c" if language == "c" else "cpp"
        source = Path(directory, "user_code." + ext)
        source.write_text(code, encoding="utf-8")
        tc = [dict(input=input_data, expected_output="", is_custom=True)]
        if language == "c":
            # Build with the original source for struct detection, then include it for line fidelity.
            harness = CRunner.build_c_harness(code, tc, ret, method, params)
        else:
            harness = SandboxRunner._build_cpp_harness(code, tc, ret, method, params)
        harness = harness.replace(code, '#include "' + source.name + '"', 1)
        harness_file = Path(directory, "harness." + ext)
        exe = str(Path(directory, "solution.exe" if os.name == "nt" else "solution"))
        stdout_file, stderr_file = Path(directory, "stdout.txt"), Path(directory, "stderr.txt")
        results_file = Path(directory, "results.json")
        # GDB on Windows passes shell redirection as argv. Redirect in the trusted
        # harness instead, so target output cannot be mixed into debugger protocol.
        redirects = '\nfreopen(' + json.dumps(stdout_file.as_posix()) + ', "w", stdout);\n'
        redirects += 'freopen(' + json.dumps(stderr_file.as_posix()) + ', "w", stderr);\n'
        harness = re.sub(r'(int main\([^)]*\)\s*\{)', lambda m: m[0] + redirects, harness, count=1)
        harness_file.write_text(harness, encoding="utf-8")
        try:
            comp = subprocess.run([compiler, "-g", "-O0", "-std=c11" if language == "c" else "-std=c++17",
                                   str(harness_file), "-o", exe, "-lm"], capture_output=True, text=True, timeout=timeout)
            if comp.returncode:
                return result("COMPILATION_ERROR", error=comp.stderr.replace(directory, ""))
            session = MI(gdb, directory, time.monotonic() + timeout)
            session.command("-gdb-set pagination off")
            session.command("-gdb-set print elements 0")
            session.command("-enable-pretty-printing", optional=True)
            session.command("-file-exec-and-symbols " + json.dumps(exe.replace("\\", "/")))
            session.command("-break-insert " + json.dumps(method if language == "c" else "Solution::" + method))
            run = 'run' + (' "' + results_file.as_posix() + '"' if language == "c" else "")
            session.command("-interpreter-exec console " + json.dumps(run))
            last_vars = {}
            while True:
                stop = session.stopped()
                reason = stop.get("reason", "")
                if reason in ("exited-normally", "exited"):
                    if stop.get("exit-code", "0") not in ("0", "00"):
                        return result("RUNTIME_ERROR", steps, "Program exited with code " + stop["exit-code"], stdout=read(stdout_file))
                    break
                if reason == "signal-received":
                    return result("RUNTIME_ERROR", steps, stop.get("signal-meaning", stop.get("signal-name", "Native signal")), stdout=read(stdout_file))
                frame = stop.get("frame", {})
                user = Path(frame.get("fullname", frame.get("file", ""))).name == source.name
                if user:
                    variables = session.command("-stack-list-variables --simple-values").get("variables", [])
                    values = {v["name"]: decode_value(v.get("value", v.get("type", "unavailable")))
                              for v in variables if v.get("name") != "this"}
                    frames = session.command("-stack-list-frames").get("stack", [])
                    stack = [f'{f["frame"].get("func", "?")} (line {f["frame"].get("line", "?")})'
                             for f in frames if Path(f["frame"].get("fullname", f["frame"].get("file", ""))).name == source.name]
                    steps.append(dict(step_index=len(steps), line=int(frame["line"]), event="line",
                                      function_name=frame.get("func", method), variables=values,
                                      changed_vars=[k for k, v in values.items() if k not in last_vars or v != last_vars[k]],
                                      call_stack=stack, stdout=""))
                    last_vars = values
                    if len(steps) >= max_steps:
                        return result("STEP_LIMIT", steps, "Trace stopped at the step limit; program completion was not established.")
                    session.command("-exec-step")
                else:
                    frames = session.command("-stack-list-frames").get("stack", [])
                    session.command("-exec-continue" if len(frames) <= 1 or
                                    Path(frame.get("fullname", frame.get("file", ""))).name == harness_file.name
                                    else "-exec-finish")
            row = json.loads(read(results_file))["results"][0] if language == "c" else payload_row(read(stdout_file))
            return completed(steps, row, read(stdout_file) if language == "c" else "")
        except (TimeoutError, subprocess.TimeoutExpired):
            return result("TIMEOUT", steps, "Native debugging timed out.")
        except (OSError, RuntimeError, ValueError, KeyError, IndexError) as exc:
            return result("ERROR", steps, str(exc))
        finally:
            if session:
                kill_tree(session.proc)


def source_lines(source_map):
    """Decode the generated-line to original-line mapping in a TypeScript source map."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    original_line, original_column, source_index = 0, 0, 0
    lines = {}
    for line, segments in enumerate(source_map.get("mappings", "").split(";"), 1):
        for segment in segments.split(","):
            values, value, shift = [], 0, 0
            for ch in segment:
                digit = alphabet.index(ch)
                value |= (digit & 31) << shift
                if digit & 32:
                    shift += 5
                else:
                    values.append(-(value >> 1) if value & 1 else value >> 1)
                    value, shift = 0, 0
            if len(values) >= 4:
                source_index += values[1]
                original_line += values[2]
                original_column += values[3]
                lines.setdefault(line, original_line + 1)
    return lines


def trace_node(code, input_data, max_steps, timeout, is_ts=False):
    node = shutil.which("node")
    if not node:
        return result("TOOLCHAIN_UNAVAILABLE", error="Node.js is required.")
    line_map = {}
    if is_ts:
        try:
            code, source_map = SandboxRunner.compile_typescript(code)
            line_map = source_lines(source_map)
        except ToolchainUnavailableError as exc:
            return result("TOOLCHAIN_UNAVAILABLE", error=str(exc))
        except ValueError as exc:
            return result("COMPILATION_ERROR", error=str(exc))
    harness = SandboxRunner._build_javascript_harness(code, [dict(input=input_data, expected_output="", is_custom=True)])
    offset = harness[:harness.index(code)].count("\n")
    user_line_count = len(code.splitlines())
    steps, proc, ws = [], None, None
    deadline = time.monotonic() + timeout
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        path = Path(directory, "solution.js")
        path.write_text(harness, encoding="utf-8")
        stdout, stderr = [], []
        errors = queue.Queue()
        try:
            proc = subprocess.Popen([node, "--inspect-brk=127.0.0.1:0", str(path)], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
            def pump(stream, collection, messages=None):
                for line in stream:
                    collection.append(line)
                    if messages is not None:
                        messages.put(line)
            readers = [threading.Thread(target=pump, args=(proc.stdout, stdout), daemon=True),
                       threading.Thread(target=pump, args=(proc.stderr, stderr, errors), daemon=True)]
            proc._debug_readers = readers
            for reader in readers:
                reader.start()
            url = None
            while time.monotonic() < deadline and not url:
                try:
                    line = errors.get(timeout=0.1)
                    match = re.search(r"ws://127\.0\.0\.1:\d+/[\w-]+", line)
                    url = match[0] if match else None
                except queue.Empty:
                    if proc.poll() is not None:
                        return result("RUNTIME_ERROR", error="".join(stderr))
            if not url:
                raise TimeoutError("Node inspector did not start")
            ws = websocket.create_connection(url, timeout=0.2, suppress_origin=True)
            pending, counter = deque(), 0

            def receive():
                while time.monotonic() < deadline:
                    try:
                        raw = ws.recv()
                        if not raw:
                            raise RuntimeError("Inspector disconnected before completion")
                        return json.loads(raw)
                    except websocket.WebSocketTimeoutException:
                        if "---SANDBOX_RESULTS_END---" in "".join(stdout):
                            return {"method": "Harness.completed"}
                        if proc.poll() is not None:
                            raise RuntimeError("Node exited before producing a complete trace")
                raise TimeoutError("Node debugging timed out")

            def rpc(method, params=None, optional=False):
                nonlocal counter
                counter += 1
                request_id = counter
                ws.send(json.dumps(dict(id=request_id, method=method, params=params or {})))
                while True:
                    reply = receive()
                    if reply.get("id") == request_id:
                        if "error" in reply and not optional:
                            raise RuntimeError(reply["error"].get("message", "Inspector command failed"))
                        return reply.get("result", {})
                    pending.append(reply)

            rpc("Runtime.enable")
            rpc("Debugger.enable")
            for line in range(offset, offset + user_line_count):
                rpc("Debugger.setBreakpointByUrl", dict(lineNumber=line, urlRegex=r"(?:^|[/\\])solution\.js$"), optional=True)
            rpc("Runtime.runIfWaitingForDebugger")
            user_script = None
            last_vars = {}
            while time.monotonic() < deadline:
                if "---SANDBOX_RESULTS_END---" in "".join(stdout):
                    break
                reply = pending.popleft() if pending else receive()
                if reply.get("method") == "Debugger.scriptParsed":
                    params = reply["params"]
                    if params.get("url", "").replace("\\", "/").endswith("/solution.js"):
                        user_script = params["scriptId"]
                if reply.get("method") != "Debugger.paused":
                    continue
                frames = reply["params"].get("callFrames", [])
                top = frames[0] if frames else {}
                loc = top.get("location", {})
                line = loc.get("lineNumber", -1) + 1 - offset
                if loc.get("scriptId") == user_script and 1 <= line <= user_line_count:
                    values = {}
                    for scope in top.get("scopeChain", []):
                        if scope["type"] not in ("local", "block", "catch"):
                            continue
                        properties = rpc("Runtime.getProperties", dict(objectId=scope["object"]["objectId"], ownProperties=True))
                        for prop in properties.get("result", []):
                            remote = prop.get("value")
                            if remote is None:
                                continue
                            val = remote.get("value", remote.get("description"))
                            if remote.get("objectId") and remote.get("type") == "object":
                                obj = rpc("Runtime.callFunctionOn", dict(objectId=remote["objectId"],
                                          functionDeclaration="function() { return this; }", returnByValue=True), optional=True)
                                val = obj.get("result", {}).get("value", val)
                            values.setdefault(prop["name"], val)
                    stack = []
                    for frame in frames:
                        frame_loc = frame["location"]
                        frame_line = frame_loc["lineNumber"] + 1 - offset
                        if frame_loc["scriptId"] == user_script and 1 <= frame_line <= user_line_count:
                            stack.append(f'{frame.get("functionName") or "anonymous"} (line {line_map.get(frame_line, frame_line)})')
                    steps.append(dict(step_index=len(steps), line=line_map.get(line, line), event="line",
                                      function_name=top.get("functionName") or "(top-level)", variables=values,
                                      changed_vars=[k for k, v in values.items() if k not in last_vars or v != last_vars[k]],
                                      call_stack=stack, stdout=""))
                    last_vars = values
                    if len(steps) >= max_steps:
                        return result("STEP_LIMIT", steps, "Trace stopped at the step limit; program completion was not established.")
                rpc("Debugger.resume")
            else:
                raise TimeoutError("Node debugging timed out")
            ws.close()
            ws = None
            proc.wait(timeout=max(0.1, deadline - time.monotonic()))
            for reader in readers:
                reader.join(timeout=1)
            if proc.returncode:
                return result("RUNTIME_ERROR", steps, "".join(stderr))
            return completed(steps, payload_row("".join(stdout)))
        except (TimeoutError, subprocess.TimeoutExpired):
            return result("TIMEOUT", steps, "Node debugging timed out.")
        except (OSError, ValueError, RuntimeError, websocket.WebSocketException) as exc:
            return result("ERROR", steps, str(exc))
        finally:
            if ws:
                ws.close()
            if proc:
                kill_tree(proc)


def trace_java(code, input_data, max_steps, timeout):
    javac, java = shutil.which("javac"), shutil.which("java")
    if not javac or not java:
        return result("TOOLCHAIN_UNAVAILABLE", error="A full JDK with the JDI debugger is required.")
    proc = None
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        try:
            sol, main = SandboxRunner._prepare_java_harness(code, [dict(input=input_data, expected_output="", is_custom=True)], directory)
            driver = str(Path(__file__).with_name("debug_support") / "TraceJava.java")
            comp = subprocess.run([javac, "--add-modules", "jdk.jdi", "-g", "-d", directory, sol, main, driver],
                                  capture_output=True, text=True, timeout=timeout)
            if comp.returncode:
                return result("COMPILATION_ERROR", error=comp.stderr.replace(directory, ""))
            proc = subprocess.Popen([java, "--add-modules", "jdk.jdi", "-cp", directory, "TraceJava", directory,
                                     str(max_steps), Path(sol).name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    encoding="utf-8", errors="replace", cwd=directory)
            stdout, stderr = proc.communicate(timeout=timeout)
            if proc.returncode:
                return result("ERROR", error=stderr or stdout)
            data = json.loads(stdout)
            if data.get("status") != "SUCCESS":
                return data
            return completed(data.get("steps", []), payload_row(data.get("stdout", "")))
        except subprocess.TimeoutExpired:
            return result("TIMEOUT", error="Java debugging timed out.")
        except (OSError, ValueError, KeyError) as exc:
            return result("ERROR", error=str(exc))
        finally:
            if proc:
                kill_tree(proc)
