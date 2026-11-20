"""Unpack the parquet files of this dataset into PNG folders and split lists.

Usage:  python tools/unpack_dataset.py <release_dir> <out_dir> [MR] [CR]

Needs only the standard library and pyarrow.
For each dataset (MR, CR) it writes
  <out_dir>/<DS>/images/<video>/<video>_frame_<NNNN>.png   (original image bytes)
  <out_dir>/<DS>/masks/<video>/<video>_frame_<NNNN>.png    (original mask bytes)
  <out_dir>/<DS>/train.txt, val.txt, test.txt
Each list line is <video>/<video>_frame_<NNNN>. This is the path below images/
and masks/ without the suffix, so it works as an MMSegmentation ann_file with
img_path='images', seg_map_path='masks' and suffix '.png'.
A frame whose split string has two parts (for example train+test) is in both lists.
"""
import csv, os, sys, glob
import pyarrow.parquet as pq

PARTS = {'train': 'train.txt', 'validation': 'val.txt', 'test': 'test.txt'}


def unpack(release, out, ds):
    files = sorted(glob.glob(os.path.join(release, ds, 'data', '*.parquet')))
    lists = {p: [] for p in PARTS}
    for f in files:
        pf = pq.ParquetFile(f)
        for batch in pf.iter_batches(batch_size=64):
            for r in batch.to_pylist():
                v, fi = r['video_id'], r['frame_index']
                stem = '%s_frame_%04d' % (v, fi)
                for kind in ('image', 'mask'):
                    d = os.path.join(out, ds, kind + 's', v)
                    os.makedirs(d, exist_ok=True)
                    with open(os.path.join(d, stem + '.png'), 'wb') as fh:
                        fh.write(r[kind]['bytes'])
                for part in r['official_split'].split('+'):
                    lists[part].append('%s/%s' % (v, stem))
    for part, name in PARTS.items():
        with open(os.path.join(out, ds, name), 'w') as fh:
            fh.write(''.join(s + '\n' for s in sorted(lists[part])))
    print(ds, len(files), 'files;', {p: len(l) for p, l in lists.items()})


if __name__ == '__main__':
    release, out = sys.argv[1], sys.argv[2]
    for ds in (sys.argv[3:] or ['MR', 'CR']):
        unpack(release, out, ds)
