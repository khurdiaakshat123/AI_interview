"""JSON transport for execution values, without guessing types from strings."""
import base64
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json
import math
import sys


def _numpy_scalar(value):
    # NumPy is already loaded when it supplies the value. Ordinary solutions do
    # not pay its import cost or acquire a new runtime dependency.
    np = sys.modules.get('numpy')
    if np is not None:
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, (np.datetime64, np.timedelta64)):
            return str(value)
        if isinstance(value, np.generic):
            native = value.item()
            if isinstance(native, np.generic):
                return Decimal(str(value)) if isinstance(value, np.floating) else str(value)
            return native
    return value


def dump_answer(value):
    """Serialize numeric library scalars as numbers, retaining Decimal digits."""
    value = _numpy_scalar(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError('Non-finite numeric answer')
        return str(int(value)) if value == value.to_integral_value() else str(value)
    if isinstance(value, (datetime, date, time, timedelta)):
        return json.dumps(str(value), ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return '[' + ','.join(dump_answer(item) for item in value) + ']'
    if isinstance(value, dict):
        entries = []
        for key, item in value.items():
            if not isinstance(key, (str, int, float, bool)) and key is not None:
                raise TypeError('JSON object keys must be scalar values')
            name = key if isinstance(key, str) else json.dumps(key, allow_nan=False)
            entries.append(json.dumps(name, ensure_ascii=False) + ':' + dump_answer(item))
        return '{' + ','.join(entries) + '}'
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _pack_cell(value):
    np = sys.modules.get('numpy')
    if np is not None:
        if isinstance(value, (np.datetime64, np.timedelta64)):
            return ['numpy_time', [str(value.astype('int64')), str(value.dtype)]]
    pd = sys.modules.get('pandas')
    if pd is not None:
        if value is pd.NA or value is pd.NaT:
            return ['null', None]
        if isinstance(value, pd.Timestamp):
            return ['timestamp', value.isoformat()]
        if isinstance(value, pd.Timedelta):
            return ['pandas_timedelta', str(value.value)]
    value = _numpy_scalar(value)
    if value is None:
        return ['null', None]
    if isinstance(value, bool):
        return ['bool', value]
    if isinstance(value, str):
        return ['str', value]
    if isinstance(value, int):
        return ['int', value]
    if isinstance(value, float):
        return ['float', repr(value)]
    if isinstance(value, Decimal):
        return ['decimal', str(value)]
    if isinstance(value, datetime):
        return ['datetime', value.isoformat()]
    if isinstance(value, date):
        return ['date', value.isoformat()]
    if isinstance(value, time):
        return ['time', value.isoformat()]
    if isinstance(value, timedelta):
        return ['timedelta', [value.days, value.seconds, value.microseconds]]
    if isinstance(value, bytes):
        return ['bytes', base64.b64encode(value).decode('ascii')]
    if isinstance(value, (list, tuple)):
        return ['tuple' if isinstance(value, tuple) else 'list', [_pack_cell(v) for v in value]]
    if isinstance(value, dict):
        return ['dict', [[_pack_cell(k), _pack_cell(v)] for k, v in value.items()]]
    # Existing tabular comparison renders other scalar objects as text.
    return ['str', str(value)]


def _unpack_cell(cell):
    kind, value = cell
    if kind == 'null':
        return None
    if kind in ('str', 'int', 'bool'):
        return value
    if kind == 'float':
        return float(value)
    if kind == 'decimal':
        return Decimal(value)
    if kind == 'numpy_time':
        import numpy as np
        return np.array(int(value[0]), dtype=value[1])[()]
    if kind in ('timestamp', 'pandas_timedelta'):
        import pandas as pd
        return pd.Timestamp(value) if kind == 'timestamp' else pd.Timedelta(int(value), unit='ns')
    if kind == 'datetime':
        return datetime.fromisoformat(value)
    if kind == 'date':
        return date.fromisoformat(value)
    if kind == 'time':
        return time.fromisoformat(value)
    if kind == 'timedelta':
        return timedelta(days=value[0], seconds=value[1], microseconds=value[2])
    if kind == 'bytes':
        return base64.b64decode(value)
    if kind in ('list', 'tuple'):
        items = [_unpack_cell(v) for v in value]
        return tuple(items) if kind == 'tuple' else items
    if kind == 'dict':
        return {_unpack_cell(k): _unpack_cell(v) for k, v in value}
    raise ValueError('Unknown execution cell type: ' + str(kind))


def pack_dataframe(frame):
    return {'version': 1, 'columns': list(frame.columns),
            'data': [[_pack_cell(cell) for cell in row] for row in frame.itertuples(index=False, name=None)]}


def unpack_dataframe(payload):
    import pandas as pd
    if payload.get('version') != 1:
        raise ValueError('Unsupported execution table format')
    rows = [[_unpack_cell(cell) for cell in row] for row in payload['data']]
    # Prevent pandas from re-inferring dates, nullable integers or mixed scalars.
    return pd.DataFrame(rows, columns=payload['columns'], dtype=object)


def json_safe_trace(value):
    if isinstance(value, float) and not math.isfinite(value):
        name = 'NaN' if math.isnan(value) else 'Infinity' if value > 0 else '-Infinity'
        return {'__type__': 'float', 'value': name}
    if isinstance(value, (list, tuple)):
        return [json_safe_trace(v) for v in value]
    if isinstance(value, dict):
        return {k: json_safe_trace(v) for k, v in value.items()}
    return value
