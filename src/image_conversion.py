import os
import glob
import rasterio
from rasterio.plot import show as rio_show  # 仍然可以用它来准备数据给matplotlib
import matplotlib.pyplot as plt
import numpy as np
import re


# --- (从您的 Streamlit 代码中复用或修改这些函数) ---
def calculate_stretch_parameters(tif_path):
    with rasterio.open(tif_path) as src:
        img_data = src.read(1).astype(np.float32)
        nodata_val = src.nodata
        if nodata_val is not None:
            img_data[img_data == np.float32(nodata_val)] = np.nan

        valid_data = img_data[~np.isnan(img_data)]
        current_vmin, current_vmax = 0.0, 1.0
        if valid_data.size > 0:
            lower_percentile = 10.0  # 您选择的拉伸参数
            upper_percentile = 85.0
            calculated_vmin = np.nanpercentile(valid_data, lower_percentile)
            calculated_vmax = np.nanpercentile(valid_data, upper_percentile)
            current_vmin = max(0.0, calculated_vmin)
            if calculated_vmax <= current_vmin:
                # ... (您之前的健壮性处理逻辑) ...
                actual_max = np.nanmax(valid_data)
                if actual_max > current_vmin:
                    current_vmax = actual_max
                else:
                    current_vmax = current_vmin + 1.0
            else:
                current_vmax = calculated_vmax
            if current_vmin == current_vmax and current_vmin == 0:
                actual_max_val = np.nanmax(valid_data)
                if actual_max_val > 0:
                    current_vmax = actual_max_val
                else:
                    current_vmax = 1.0
        return img_data, src.transform, current_vmin, current_vmax, src.crs  # 返回需要的信息


def save_stretched_tif_as_png(tif_path, output_png_path, cmap='hot'):
    img_data, transform, vmin, vmax, crs = calculate_stretch_parameters(tif_path)

    fig, ax = plt.subplots(figsize=(10, 8))  # 根据需要调整
    # 使用 rasterio.plot.show 来正确地根据地理参考信息显示数据
    rio_show(img_data,
             transform=transform,
             ax=ax,
             cmap=cmap,
             vmin=vmin,
             vmax=vmax)

    # 如果需要，可以有条件地在这里添加底图到PNG中，但如果您希望Streamlit中快速切换，
    # 且底图对于所有年份都一样，也可以考虑在Streamlit中将PNG作为前景，底图作为背景独立处理。
    # 但最简单的方法是直接保存没有底图的灯光图层。

    ax.set_axis_off()  # 去掉坐标轴边框和刻度
    fig.savefig(output_png_path, format='png', bbox_inches='tight', pad_inches=0, dpi=100)  # pad_inches=0 确保无白边
    plt.close(fig)
    print(f"Saved: {output_png_path}")


if __name__ == '__main__':
    TIF_FILE_DIRECTORY = "."  # TIF输入目录
    FILE_PATTERN = "DMSP-like*.tif"
    OUTPUT_PNG_DIRECTORY = "./processed_nightlights"  # PNG输出目录

    if not os.path.exists(OUTPUT_PNG_DIRECTORY):
        os.makedirs(OUTPUT_PNG_DIRECTORY)

    search_path = os.path.join(TIF_FILE_DIRECTORY, FILE_PATTERN)
    tif_files_paths = sorted(glob.glob(search_path))

    if not tif_files_paths:
        print(f"No TIF files found matching '{FILE_PATTERN}' in '{TIF_FILE_DIRECTORY}'")
    else:
        for tif_path in tif_files_paths:
            filename = os.path.basename(tif_path)
            year_match = re.findall(r'(\d{4})', filename)
            if year_match:
                year = year_match[-1]
                output_png_filename = f"{year}.png"  # 或者更详细的命名
                output_png_path = os.path.join(OUTPUT_PNG_DIRECTORY, output_png_filename)
                save_stretched_tif_as_png(tif_path, output_png_path)
            else:
                print(f"Could not extract year from {filename}")


#C:\\Users\\12907\\Desktop\\2024-2025大二下学期\\NTL-Data-Analysis-a-GIS-Software-Engineering-Project\\src\\processed_nightlights