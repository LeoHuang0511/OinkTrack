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
## Evaluation
## Demo 
