# OinkTrack
## Dataset
Download the dataset from [Google Drive](https://drive.google.com/drive/folders/1G9ygFt_G6f4SUguMmxCgKxRFgmVpmYSE?usp=drive_link).


Organize as follows:
~~~
{OinkTrack ROOT}
|-- OinkTrack
|   |-- C1D-1
|   |   |-- raw_videos
|   |   |   |-- 20241206_075959_080059
|   |   |       |-- 1733443200-1733443214.ts
|   |   |       |-- 1733443215-1733443229.ts
|   |   |       |-- ...
|   |   |-- annotation.json
|   |-- C1D-2
|   |-- C1D-3
|   |-- ...
|   |-- mask
        |-- C1_mask.png
        |-- C2_mask.png
~~~

Each folder under `OinkTrack` corresponds to a specific scene and lighting condition:

* `C1D-*`, `C1N-*`, `C1DN-*`, etc.:

  * `C1` and `C2` refer to different camera views .
  * `D` = Daytime, `N` = Nighttime, `DN` = Day-to-Night transition, `ND` = Night-to-Day transition.

## Build a MOT-style dataset

This repository ships a helper script, **`make_dataset.py`**, that converts the raw OinkTrack recordings ( `.ts` clips + `annotation.json`) into a standard **MOTChallenge** layout (`img1/`, `gt/gt.txt`, `seqinfo.ini`, 1 fps).

### 1 · Folder layout before running

~~~
project_root
|-- make_dataset.py          ← the script (keep here)
|-- OinkTrack               ← downloaded from Google Drive
~~~

### 2 · Quick start

```bash
# From project_root
python make_dataset.py
```
### 3 · Output

After running make_dataset.py, the following folder structure will be generated:
~~~
project_root
|-- make_dataset.py
|-- OinkTrack 
|-- dataset # generated MOT-style dataset
~~~
The structure of dataset/ is as follows:
~~~

dataset
|-- train
|   |-- C1D-1
|   |   |-- img1
|   |   |   |-- 00000001.jpg
|   |   |   |-- 00000002.jpg
|   |   |   |-- ...
|   |   |-- gt
|   |   |   |-- gt.txt
|   |   |-- seqinfo.ini
|   |--...
|-- val
|   |-- ...
|-- test
|   |-- ...
|-- train_seqmap.txt
|-- val_seqmap.txt
|-- test_seqmap.txt


~~~
Each line in `gt.txt` contains:

```

<frame>, <id>, <bb_left>, <bb_top>, <bb_width>, <bb_height>, 1, 1, 1
```


### 4 · Customising the split

Open the header of **`make_dataset.py`** and edit the `SPLIT` dictionary:

```python
SPLIT: dict[str, list[str]] = {
    "train": ["C1D-1", "C1D-3", ...],
    "val":   [...],
    "test":  [...],
}
```

Save, rerun the script, and the output folders & `*_seqmap.txt` files will be regenerated accordingly.

## Evaluation
For the tracking-by-detection models, we provide the weights of detector pre-trained on OinkTrack [here]. Additionally, we also provide the weights of transformer-based models pre-trained on OinkTrack, such as MOTR[link], MeMOTR[link], MOTIP[link].

We organize the results of test set as follows:
~~~
{DanceTrack ROOT}
|-- val
|   |-- TRACKER_NAME
|   |   |-- dancetrack000x.txt
|   |   |-- ...
|   |-- ...
~~~
where dancetrack000x.txt is the output file of the video episode dancetrack000x, each line of which contains:
~~~
<frame>, <id>, <bb_left>, <bb_top>, <bb_width>, <bb_height>, <conf>, -1, -1, -1
~~~

Then, simply run the evalution code:
```
python3 TrackEval/scripts/run_mot_challenge.py --SPLIT_TO_EVAL val  --METRICS HOTA CLEAR Identity  --GT_FOLDER dancetrack/val --SEQMAP_FILE dancetrack/val_seqmap.txt --SKIP_SPLIT_FOL True   --TRACKERS_TO_EVAL '' --TRACKER_SUB_FOLDER ''  --USE_PARALLEL True --NUM_PARALLEL_CORES 8 --PLOT_CURVES False --TRACKERS_FOLDER val/TRACKER_NAME 
```
## Demo 
![OinkTrack Demo](assets/visualized_day.gif)
