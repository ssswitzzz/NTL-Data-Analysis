import streamlit as st
import os
import glob
import re
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
from folium.plugins import HeatMap, SideBySideLayers, MarkerCluster
import pydeck as pdk
from matplotlib import cm
from matplotlib.colors import Normalize



st.set_page_config(layout="wide")

# 这个CSS代码是为了消除folium地图下方的大片空白，参考来源https://discuss.streamlit.io/t/folium-map-white-space-under-the-map-on-the-first-rendering/84363
st.markdown("""
    <style>
        iframe[title="streamlit_folium.st_folium"] { 
            height: 700px !important;
        }
    </style>
""", unsafe_allow_html=True)

abspath = os.path.dirname(os.path.abspath(__file__))
png_dir = os.path.join(abspath, "processed_nightlights")
file = "*.png"
yearly_provinces_shp_dir= os.path.join(abspath, "yearly_nightlight_stats_provinces")
yearly_cities_shp_dir= os.path.join(abspath, "yearly_nightlight_stats_cities")
china_boundary_dir=os.path.join(abspath, "CN_boundary")
province = "省"


@st.cache_data
def load_yearly_data(shp_path):
    gdf = gpd.read_file(shp_path)
    gdf.loc[32, 'ENG_NAME'] = 'Macao'
    return gdf


@st.cache_data
def load_china_boundary(shp_path):
    gdf = gpd.read_file(shp_path)
    return gdf


@st.cache_data
# 这个用来返回每年夜间灯光值的路径、属性表列的字典
def generate_shapefile_dict(directory):
    year_data_map = {}
    pattern = os.path.join(directory, "NTL_*.shp")
    for shp in glob.glob(pattern):
        filename = os.path.basename(shp)
        match = re.search(r'(\d{4})', filename)  # 查找文件名中的四位数字作为年份
        if match:
            year = match.group(1)
            data_column_name = f"NTL_{year}_m"
            year_data_map[year] = {"path": shp, "data_column": data_column_name}

    sorted_years = sorted(year_data_map.keys(), reverse=True)
    return {year: year_data_map[year] for year in sorted_years}


def generate_shapefile_dict_for_cities(directory):
    year_data_map = {}
    pattern = os.path.join(directory, "NTL_*_cities.shp")
    for shp in glob.glob(pattern):
        filename = os.path.basename(shp)
        match = re.search(r'(\d{4})', filename)  # 查找文件名中的四位数字作为年份
        if match:
            year = match.group(1)
            data_column_name = f"NTL_{year}_m"
            year_data_map[year] = {"path": shp, "data_column": data_column_name}

    sorted_years = sorted(year_data_map.keys(), reverse=True)
    return {year: year_data_map[year] for year in sorted_years}


@st.cache_data
# 返回一个整合各个省份从1992到2022年的每年平均夜间灯光值的DataFrame
def generate_yearly_ntl_dataframe(year_dict, province):
    data = []
    for year_str, year_info in year_dict.items():
        gdf_year = load_yearly_data(year_info["path"])
        ntl_col = year_info["data_column"]
        gdf_year[ntl_col] = pd.to_numeric(gdf_year[ntl_col], errors='coerce')
        for index, row in gdf_year.iterrows():
            data.append({
                "Year": int(year_str),
                province: row[province],
                "NTL_Value": row[ntl_col]
            })
    return pd.DataFrame(data)

def main():

    st.title("中国省级年度夜间灯光强度交互式地图:world_map:")

    game_html = """
    <div id="game-container" style="text-align:center; padding:20px; border:1px solid #ddd;">
        <h3>等待时点我!</h3>
        <button id="clickButton" onclick="incrementScore()">点击!</button>
        <p>分数: <span id="score">0</span></p>
    </div>
    <script>
        let score = 0;
        function incrementScore() {
            score++;
            document.getElementById('score').innerText = score;
        }
    </script>
    """




    st.sidebar.header("地图选项:thinking_face:")
    year_dict_provinces = generate_shapefile_dict(yearly_provinces_shp_dir)
    sorted_years_list = list(year_dict_provinces.keys())
    year_dict_cities = generate_shapefile_dict_for_cities(yearly_cities_shp_dir)

    selected_year = st.sidebar.selectbox("选择年份:", sorted_years_list)

    selected_year_info_provinces= year_dict_provinces[selected_year]
    selected_shp_path_provinces = selected_year_info_provinces["path"]
    selected_ntl_column = selected_year_info_provinces["data_column"]

    selected_year_info_cities = year_dict_cities[selected_year]
    selected_shp_path_cities = selected_year_info_cities["path"]

    view_mode = st.sidebar.radio(
        "选择地图视角:",
        ('2D 平面视图 (Folium)', '3D 立体视图 (Pydeck)'),
        key="view_mode_select"
    )

    # 定义可选的Brewer颜色方案
    available_color_schemes = [
        'YlOrRd', 'PuBu', 'BuPu', 'OrRd', 'RdPu', 'BuGn', 'GnBu', 'PuBuGn',
        'PuRd', 'Blues', 'Greens', 'Greys', 'Oranges', 'Purples', 'Reds',
        'YlGn', 'YlGnBu', 'YlOrBr'
    ]
    selected_color_scheme = st.sidebar.selectbox(
        "选择配色方案:",
        available_color_schemes,
        index=available_color_schemes.index('YlOrRd')
    )

    if view_mode == '2D 平面视图 (Folium)':
        num_bins = st.sidebar.slider("选择分级数量 (2D地图):", min_value=3, max_value=20, value=7, step=1)

    if view_mode == '3D 立体视图 (Pydeck)':
        elevation_multiplier = st.sidebar.slider("调整立体拉伸倍数 (3D地图):", min_value=5000, max_value=100000,
                                                 value=20000, step=5000)

    st.sidebar.info(f"当前显示年份: {selected_year}")
    st.sidebar.info(f"数据文件: {os.path.basename(selected_shp_path_provinces)}")
    st.sidebar.info(f"灯光数据列: {selected_ntl_column}")
    st.sidebar.info(f"当前配色方案: {selected_color_scheme}")

    map_progress_bar = st.progress(0)
    st.components.v1.html(game_html, height=200)
    # 加载选定年份的数据，其实就是得到Shapefile的属性表
    gdf_provinces_yearly = load_yearly_data(selected_shp_path_provinces)
    gdf_cities_yearly = load_yearly_data(selected_shp_path_cities)
    china_boundary=load_china_boundary(china_boundary_dir)

    # 这里计算灯光强度占比
    gdf_provinces_yearly[selected_ntl_column] = pd.to_numeric(gdf_provinces_yearly[selected_ntl_column],errors='coerce')
    total_ntl_this_year = gdf_provinces_yearly[selected_ntl_column].fillna(0).sum()
    proportion_column_name = f"NTL_{selected_year}_占比"
    gdf_provinces_yearly[proportion_column_name] = (gdf_provinces_yearly[selected_ntl_column] / total_ntl_this_year)

    if view_mode == '2D 平面视图 (Folium)':
        m = folium.Map((35.8617, 104.1954), zoom_start=4, tiles='cartodbpositron')
        data_for_map = gdf_provinces_yearly[[province, selected_ntl_column,proportion_column_name, 'geometry']].copy()

        map_progress_bar.progress(30)

        choropleth_layer = folium.Choropleth(
            geo_data=data_for_map.to_json(),
            name=f'灯光强度 {selected_year}',
            data=data_for_map,
            columns=[province, selected_ntl_column,proportion_column_name],
            key_on=f'feature.properties.{province}',
            fill_color=selected_color_scheme,
            fill_opacity=0.7,
            line_opacity=0.3,
            legend_name=f'{selected_year}年 夜间灯光平均强度',
            highlight=True,
            bins=num_bins
        ).add_to(m)

        map_progress_bar.progress(50)

        folium.GeoJsonTooltip(
            fields=[province, selected_ntl_column,proportion_column_name],
            aliases=['省份/区域:', f'{selected_year}年灯光强度:',f'{selected_year}年{province}灯光强度在全国中的占比'],
            sticky=False,
            localize=True,
            style="""
                background-color: #F0EFEF;
                border: 2px solid black;
                border-radius: 3px;
                box-shadow: 3px;
            """
        ).add_to(choropleth_layer.geojson)

        map_progress_bar.progress(60)

        st.sidebar.markdown("---")
        st.sidebar.write("其他选项：")

        show_cluster_option = st.sidebar.checkbox("查看市级灯光强度标记簇")
        show_layer_option = st.sidebar.checkbox('使用并排底图')
        show_antpath_option = st.sidebar.checkbox('添加国界流动线', value=False)

        if show_cluster_option:
            map_progress_bar.progress(65)
            marker_cluster = MarkerCluster(name=f"{selected_year}年城市灯光点").add_to(m)

            for index, row in gdf_cities_yearly.iterrows():
                ntl_value = row[selected_ntl_column]
                if pd.notna(ntl_value) and row['geometry'] and not row['geometry'].is_empty:
                    centroid = row['geometry'].centroid
                    tooltip_text = f"{row['NAME']} - 灯光强度: {ntl_value:.2f}"
                    folium.Marker(
                        location=[centroid.y, centroid.x],
                        tooltip=tooltip_text,
                        icon=folium.Icon(color='blue', icon='circle-arrow-down', prefix='glyphicon')
                    ).add_to(marker_cluster)
            map_progress_bar.progress(75)

        layer_right = folium.TileLayer('openstreetmap')
        layer_left = folium.TileLayer('cartodbpositron')
        if show_layer_option:
            sbs = SideBySideLayers(layer_left=layer_left, layer_right=layer_right)
            layer_left.add_to(m)
            layer_right.add_to(m)
            sbs.add_to(m)

        # 这里添加AntPath
        if show_antpath_option:
            if china_boundary.crs and china_boundary.crs.to_epsg() != 4326:
                china_boundary = china_boundary.to_crs(epsg=4326)
            ant_path_segment_coords_list = []

            for index, row in china_boundary.iterrows():
                geometry = row['geometry']
                current_segment_coords = [(lat, lon) for lon, lat in list(geometry.coords)]
                ant_path_segment_coords_list.append(current_segment_coords)

            ant_path_layer = folium.plugins.AntPath(
                locations=ant_path_segment_coords_list,
                dash_array=[5, 60],
                delay=1000,
                weight=2,
                color="black",
                pulse_color="white",
                hardware_acceleration=True,
                name="国界分段动态路径 (AntPath)"
            )
            ant_path_layer.add_to(m)

        folium.LayerControl().add_to(m)

        # 生成地图主要界面
        st.subheader(f"{selected_year}年 中国省级夜间灯光强度分布图:cityscape:(配色方案: {selected_color_scheme})")
        with st.spinner("正在生成地图..."):
            st_folium(m, width=1200, height=700, returned_objects=[])

        container1 = st.container(border=True)
        container1.latex('注1：港澳台地区无数据')
        container1.latex('注2；灯光强度占比保留到小数后3位，如果显示0，则是占比太小')
        map_progress_bar.progress(100)

    elif view_mode == '3D 立体视图 (Pydeck)':
        st.subheader(f"{selected_year}年 中国省级夜间灯光强度分布图 (3D):earth_asia:")
        with st.spinner("正在生成 3D 地图..."):

            data_for_3d = gdf_provinces_yearly.dropna(subset=[selected_ntl_column]).copy()

            # 最重要的一步！！！使用 explode() 将 MultiPolygon 转换为 Polygon，不然图层显示不出来，就只有底图了
            data_for_3d = data_for_3d.explode(index_parts=True)

            # Pydeck的PolygonLayer需要一个包含多边形顶点坐标的列
            data_for_3d['coordinates'] = data_for_3d['geometry'].apply(lambda x: [list(x.exterior.coords)])
            map_progress_bar.progress(30)

            # 对灯光强度进行拉伸，不然全都是黑的
            min_value, max_value = data_for_3d[selected_ntl_column].min(), data_for_3d[selected_ntl_column].max()
            normalize = Normalize(vmin=min_value, vmax=max_value)
            cmap = cm.get_cmap(selected_color_scheme)

            def get_color(value):
                rgba = cmap(normalize(value))
                return [int(c * 255) for c in rgba[:3]]

            data_for_3d['fill_color'] = data_for_3d[selected_ntl_column].apply(get_color)

            province_layer = pdk.Layer(
                'PolygonLayer',
                data=data_for_3d,
                get_polygon='coordinates',
                filled=True,
                stroked=True,
                extruded=True,
                get_elevation=selected_ntl_column,
                elevation_scale=elevation_multiplier,
                get_fill_color='fill_color',
                get_line_color=[255, 255, 255, 50],
                line_width_min_pixels=1,
                pickable=True,
                auto_highlight=True
            )
            map_progress_bar.progress(50)
            layers_to_render = [province_layer]

            gdf_border = load_china_boundary(china_boundary_dir)
            gdf_border_exploded = gdf_border.explode(index_parts=False)

            gdf_border_exploded['path'] = gdf_border_exploded['geometry'].apply(lambda x: list(x.coords))
            map_progress_bar.progress(70)
            border_layer = pdk.Layer(
                'PathLayer',
                data=gdf_border_exploded,
                get_path='path',
                get_color=[0, 0, 0, 180],
                width_min_pixels=1.5,
                pickable=False
            )
            layers_to_render.append(border_layer)

            view_state = pdk.ViewState(longitude=104.1954, latitude=35.8617, zoom=3.5, pitch=50, bearing=0)
            tooltip = {
                "html": f"<b>省份:</b> {{{'省'}}}<br/><b>{selected_year}年平均灯光强度:</b> {{{selected_ntl_column}}}"}

            deck = pdk.Deck(layers=layers_to_render, initial_view_state=view_state, map_style='light', tooltip=tooltip)
            st.pydeck_chart(deck)

    st.balloons()

    map_progress_bar.empty()

    consolidated_df = generate_yearly_ntl_dataframe(year_dict_provinces, province)
    consolidated_df['Year'] = pd.to_numeric(consolidated_df['Year'],errors='coerce')
    consolidated_df = consolidated_df.sort_values(by=['Year', province])

    # 创建累积数据的DataFrame，每一年的数据都会包含小于等于这个年份的所有数据，从而在下方实现折线图动画
    sorted_years = sorted(consolidated_df['Year'].unique())
    cumulative_list = []

    for year in sorted_years:
        animation_df = consolidated_df[consolidated_df['Year'] <= year].copy()
        animation_df['animation_frame_id'] = year
        cumulative_list.append(animation_df)

    cumulative_plot_df = pd.concat(cumulative_list)

    st.subheader("所有省份夜间灯光强度历年变化趋势（动画）:chart_with_upwards_trend:")
    container=st.container(border=True)
    container.markdown('**提示：单击图例可以隐藏不想查看的省份，双击图例可以单独查看某一个省份，双击后再单击可以单独查看多个省份**')

    with st.spinner("正在生成动画折线图"):

        fig_all_provinces = px.line(
            cumulative_plot_df,
            x="Year",
            y="NTL_Value",
            color="省",
            line_group="省",
            animation_frame="animation_frame_id",
            animation_group="省",
            markers=True,
            labels={
                "Year": "年份",
                "NTL_Value": f"平均灯光强度",
                "省": "省份/区域",
                "animation_frame_id": "动画播放年份"
            },
            width = 1000, height = 600,
            color_discrete_sequence = px.colors.qualitative.Light24
        )


        #这个设置的参考来源https://stackoverflow.com/questions/70523979/how-to-create-an-animated-line-plot-with-ploty-express
        fig_all_provinces.layout.updatemenus[0].buttons[0].args[1]['frame']['redraw'] = True

        st.plotly_chart(fig_all_provinces, use_container_width=True)



if __name__ == '__main__':
    main()