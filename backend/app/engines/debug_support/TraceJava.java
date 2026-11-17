import com.sun.jdi.*;
import com.sun.jdi.connect.*;
import com.sun.jdi.event.*;
import com.sun.jdi.request.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** JDI event driver. Candidate source is compiled unchanged in its own file. */
public final class TraceJava {
    static String quote(String s) {
        StringBuilder out = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            if (c == '"' || c == '\\') out.append('\\').append(c);
            else if (c < 32) out.append(String.format("\\u%04x", (int)c));
            else out.append(c);
        }
        return out.append('"').toString();
    }

    static String value(Value v, Set<Long> visited, int depth) {
        if (v == null) return "null";
        if (v instanceof StringReference) return quote(((StringReference)v).value());
        if (v instanceof CharValue) return quote(String.valueOf(((CharValue)v).value()));
        if (v instanceof PrimitiveValue) return v.toString();
        ObjectReference obj = (ObjectReference)v;
        if (depth > 5 || !visited.add(obj.uniqueID())) return quote(obj.referenceType().name() + "@" + obj.uniqueID());
        try {
            if (obj instanceof ArrayReference) {
                StringJoiner out = new StringJoiner(",", "[", "]");
                for (Value item : ((ArrayReference)obj).getValues()) out.add(value(item, visited, depth + 1));
                return out.toString();
            }
            StringJoiner out = new StringJoiner(",", "{", "}");
            for (Field field : obj.referenceType().allFields()) {
                if (!field.isStatic()) out.add(quote(field.name()) + ":" + value(obj.getValue(field), visited, depth + 1));
            }
            return out.toString();
        } finally { visited.remove(obj.uniqueID()); }
    }

    static Thread drain(InputStream stream, ByteArrayOutputStream target) {
        Thread thread = new Thread(() -> {
            try { stream.transferTo(target); } catch (IOException ignored) { }
        });
        thread.setDaemon(true); thread.start(); return thread;
    }

    public static void main(String[] args) throws Exception {
        LaunchingConnector connector = Bootstrap.virtualMachineManager().defaultConnector();
        Map<String, Connector.Argument> settings = connector.defaultArguments();
        settings.get("main").setValue("Main");
        settings.get("options").setValue("-cp \"" + args[0] + "\"");
        VirtualMachine vm = connector.launch(settings);
        Process process = vm.process();
        ByteArrayOutputStream stdout = new ByteArrayOutputStream(), stderr = new ByteArrayOutputStream();
        Thread outReader = drain(process.getInputStream(), stdout), errReader = drain(process.getErrorStream(), stderr);
        int maxSteps = Integer.parseInt(args[1]);
        List<String> steps = new ArrayList<>();
        Map<String, String> last = new HashMap<>();
        boolean done = false, limited = false, normalDeath = false;
        String failure = null;
        EventRequestManager manager = vm.eventRequestManager();
        ClassPrepareRequest prepare = manager.createClassPrepareRequest();
        prepare.setSuspendPolicy(EventRequest.SUSPEND_ALL); prepare.enable();
        vm.resume();
        try {
            while (!done) {
                EventSet events = vm.eventQueue().remove();
                for (Event event : events) {
                    if (event instanceof ClassPrepareEvent) {
                        ReferenceType type = ((ClassPrepareEvent)event).referenceType();
                        try {
                            // Harness and JDK lines must never appear as candidate steps.
                            if (type.sourceName().equals(args[2])) {
                                Set<String> installed = new HashSet<>();
                                for (Location loc : type.allLineLocations()) {
                                    String key = loc.method().name() + ":" + loc.codeIndex();
                                    if (installed.add(key)) {
                                        BreakpointRequest bp = manager.createBreakpointRequest(loc);
                                        bp.setSuspendPolicy(EventRequest.SUSPEND_ALL); bp.enable();
                                    }
                                }
                            }
                        } catch (AbsentInformationException ignored) { }
                    } else if (event instanceof BreakpointEvent) {
                        BreakpointEvent hit = (BreakpointEvent)event;
                        Location loc = hit.location();
                        StackFrame frame = hit.thread().frame(0);
                        Map<String, String> variables = new LinkedHashMap<>();
                        try {
                            for (LocalVariable variable : frame.visibleVariables()) {
                                variables.put(variable.name(), value(frame.getValue(variable), new HashSet<>(), 0));
                            }
                        } catch (AbsentInformationException ignored) { }
                        StringJoiner vars = new StringJoiner(",", "{", "}");
                        StringJoiner changed = new StringJoiner(",", "[", "]");
                        for (Map.Entry<String, String> entry : variables.entrySet()) {
                            vars.add(quote(entry.getKey()) + ":" + entry.getValue());
                            if (!Objects.equals(last.get(entry.getKey()), entry.getValue())) changed.add(quote(entry.getKey()));
                        }
                        last = variables;
                        StringJoiner stack = new StringJoiner(",", "[", "]");
                        for (StackFrame parent : hit.thread().frames()) {
                            if (parent.location().declaringType().equals(loc.declaringType()))
                                stack.add(quote(parent.location().method().name() + " (line " + parent.location().lineNumber() + ")"));
                        }
                        steps.add("{\"step_index\":" + steps.size() + ",\"line\":" + loc.lineNumber() +
                                  ",\"event\":\"line\",\"function_name\":" + quote(loc.method().name()) +
                                  ",\"variables\":" + vars + ",\"changed_vars\":" + changed +
                                  ",\"call_stack\":" + stack + ",\"stdout\":\"\"}");
                        if (steps.size() >= maxSteps) { limited = true; done = true; break; }
                    } else if (event instanceof VMDeathEvent) {
                        normalDeath = true; done = true;
                    } else if (event instanceof VMDisconnectEvent) {
                        done = true;
                    }
                }
                if (!limited) events.resume();
            }
        } catch (VMDisconnectedException ignored) {
            done = true;
        } catch (Exception error) {
            failure = error.toString();
        } finally {
            if (limited || failure != null || !normalDeath) process.destroyForcibly();
            try { vm.dispose(); } catch (VMDisconnectedException ignored) { }
        }
        process.waitFor(); outReader.join(); errReader.join();
        String status = limited ? "STEP_LIMIT" : failure != null ? "ERROR" :
                        normalDeath && process.exitValue() == 0 ? "SUCCESS" : "RUNTIME_ERROR";
        String error = limited ? "Trace stopped at the step limit; program completion was not established." :
                       failure != null ? failure : status.equals("SUCCESS") ? null : stderr.toString(StandardCharsets.UTF_8);
        System.out.println("{\"status\":" + quote(status) + ",\"steps\":[" + String.join(",", steps) +
                           "],\"total_steps\":" + steps.size() + ",\"max_steps_reached\":" + limited +
                           ",\"return_value\":null,\"error\":" + (error == null ? "null" : quote(error)) +
                           ",\"stdout\":" + quote(stdout.toString(StandardCharsets.UTF_8)) + "}");
    }
}
