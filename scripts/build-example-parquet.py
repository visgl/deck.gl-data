"""Build full example tables. Requires pyarrow==21.0.0; run from any directory.

Meteorite and earthquake decoding follows deck.gl's MIT-licensed website workers.
Cities use the original CSV: the compact website file loses negative latitudes.
"""
import csv
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def number(text):
    """Decode the website format's unsigned base-90 integer."""
    value = 0
    for char in text:
        value = value * 90 + ord(char) - 32
    return value


def coordinates(text):
    """Decode the meteorite coordinate dictionary's Google encoded polyline."""
    values = []
    index = 0
    position = [0, 0]
    while index < len(text):
        for axis in range(2):
            result = shift = 0
            while True:
                byte = ord(text[index]) - 63
                index += 1
                result |= (byte & 31) << shift
                shift += 5
                if byte < 32:
                    break
            position[axis] += ~(result >> 1) if result & 1 else result >> 1
        values.append([position[1] / 1e5, position[0] / 1e5])
    return values


def cities():
    """Preserve every CSV city, including its original signed coordinates."""
    with (ROOT / 'examples/text-layer/cities-1000.csv').open(encoding='utf-8', newline='') as source:
        return [dict(name=r['name'], population=int(r['population']),
                     longitude=float(r['longitude']), latitude=float(r['latitude']))
                for r in csv.DictReader(source)]


def meteorites():
    """Expand coordinate dictionary references without dropping unknown years."""
    lines = (ROOT / 'website/meteorites.txt').read_text(encoding='utf-8').splitlines()
    points = coordinates(lines[0])
    rows = []
    for line in lines[1:]:
        parts = line.split('\t')
        if len(parts) >= 5:
            rows.append(dict(name=parts[0], **{'class': parts[1]},
                             coordinates=points[number(parts[2])],
                             mass=number(parts[3]), year=number(parts[4])))
    return rows


def earthquakes():
    """Expand delta timestamps and scaled values in source order."""
    timestamp = 0
    rows = []
    for line in (ROOT / 'website/earthquakes.txt').read_text(encoding='utf-8').split('\n'):
        if not line:
            continue
        time, rest = line[1:].split('\x01')
        timestamp += number(time)
        rows.append(dict(timestamp=float(timestamp),
                         latitude=(number(rest[:4]) - 900000) / 10000,
                         longitude=(number(rest[4:8]) - 1800000) / 10000,
                         depth=(number(rest[8:]) - 300) / 100,
                         magnitude=(number(line[0]) + 30) / 10))
    return rows


if __name__ == '__main__':
    for path, rows, count in [
        ('examples/text-layer/cities-1000.parquet', cities(), 140867),
        ('examples/icon/meteorites.parquet', meteorites(), 45716),
        ('examples/data-filter/earthquakes.parquet', earthquakes(), 218396)
    ]:
        assert len(rows) == count, (path, len(rows))
        table = pa.Table.from_pylist(rows)
        if 'coordinates' in table.column_names:
            index = table.column_names.index('coordinates')
            table = table.set_column(index, 'coordinates',
                                    pa.array([r['coordinates'] for r in rows],
                                             type=pa.list_(pa.float64(), 2)))
        # JavaScript accessors expect numbers, not Arrow int64 BigInts.
        for index, field in enumerate(table.schema):
            if pa.types.is_int64(field.type):
                table = table.set_column(index, field.name, table.column(index).cast(pa.float64()))
        output = ROOT / path
        output.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, output, compression='zstd', compression_level=9,
                       use_dictionary=False)
        assert pq.read_table(output).equals(table)
        print(f'{path}: {count:,} rows, {output.stat().st_size:,} bytes')
