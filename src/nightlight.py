import streamlit as st
import time
import os
import glob
import re

# --- (假设您已经有了 load_all_image_bytes 和相关的配置) ---
PNG_FILE_DIRECTORY = "C:\\Users\\12907\\Desktop\\2024-2025大二下学期\\NTL-Data-Analysis-a-GIS-Software-Engineering-Project\\src\\processed_nightlights"
FILE_PATTERN = "*.png"
ANIMATION_SPEED_SECONDS_INTERACTIVE = 0.2  # 用于 rerun 方法
ANIMATION_SPEED_SECONDS_ONCE = 0.1  # 用于阻塞循环方法


def load_all_image_bytes(_year_to_file_map_tuple):
    # ... (您的 load_all_image_bytes 函数实现) ...
    # 返回一个例如 {'year': image_bytes, ...} 的字典
    year_to_file_map = dict(_year_to_file_map_tuple)
    images_bytes_dict = {}
    for year, file_path in year_to_file_map.items():
        with open(file_path, 'rb') as f:
            images_bytes_dict[year] = f.read()
    return images_bytes_dict


def main():
    st.title("夜间灯光地图")

    # ... (代码加载文件路径，创建 year_to_file_path_map 和 sorted_years) ...
    search_path = os.path.join(PNG_FILE_DIRECTORY, FILE_PATTERN)
    png_files_paths = sorted(glob.glob(search_path))
    year_to_file_path_map = {}
    for png_path in png_files_paths:
        filename = os.path.basename(png_path)
        year_match = re.match(r'(\d{4})\.png', filename)
        if year_match:
            year = year_match.group(1)
            year_to_file_path_map[year] = png_path
    sorted_years = sorted(list(year_to_file_path_map.keys()))
    if not sorted_years:
        st.error("No images found.")
        return

    year_to_file_path_map_tuple = tuple(year_to_file_path_map.items())
    all_loaded_images_bytes = load_all_image_bytes(year_to_file_path_map_tuple)



    # --- "播放完整动画（一次性）" 按钮 ---
    st.markdown("---")
    if st.button("播放完整动画（一次性，无交互）"):
        st.session_state.playing_interactive = False  # 确保交互式动画停止
        animation_placeholder_once = st.empty()
        st.write("正在播放完整动画...")
        for year in sorted_years:  # 假设我们从头播放
            img_bytes = all_loaded_images_bytes.get(year)
            if img_bytes:
                animation_placeholder_once.image(img_bytes, use_container_width=True)
                time.sleep(ANIMATION_SPEED_SECONDS_ONCE)  # 使用为一次性播放调整的速度
            # 在这个循环中，st.session_state.current_year_index 不会被更新以驱动滑动条
        animation_placeholder_once.empty()  # 播放完毕后可以清空

    # --- 地图显示区域 (用于交互式) ---
    # --- 交互式部分 (使用 rerun) ---
    if 'playing_interactive' not in st.session_state:
        st.session_state.playing_interactive = False
    if 'current_year_index' not in st.session_state or st.session_state.current_year_index >= len(sorted_years):
        st.session_state.current_year_index = 0

    selected_year_str = st.select_slider(
        "选择年份 (交互式)",
        options=sorted_years,
        value=sorted_years[st.session_state.current_year_index],
        key="year_slider_interactive"
    )
    new_slider_index = sorted_years.index(selected_year_str)
    if new_slider_index != st.session_state.current_year_index:
        st.session_state.current_year_index = new_slider_index
        st.session_state.playing_interactive = False  # 滑动时停止播放

    play_button_label = "暂停交互动画" if st.session_state.playing_interactive else "播放交互动画"
    if st.button(play_button_label):
        st.session_state.playing_interactive = not st.session_state.playing_interactive
        if st.session_state.playing_interactive:
            st.session_state.current_year_index = sorted_years.index(selected_year_str)
    map_placeholder_interactive = st.empty()
    current_display_year = sorted_years[st.session_state.current_year_index]
    image_bytes_to_display = all_loaded_images_bytes.get(current_display_year)
    if image_bytes_to_display:
        map_placeholder_interactive.image(image_bytes_to_display, use_container_width=True)
    st.caption(f"当前显示 (交互式): {current_display_year} 年")

    if st.session_state.playing_interactive:
        next_year_index = (st.session_state.current_year_index + 1) % len(sorted_years)
        st.session_state.current_year_index = next_year_index
        time.sleep(ANIMATION_SPEED_SECONDS_INTERACTIVE)
        st.rerun()


if __name__ == '__main__':
    main()
