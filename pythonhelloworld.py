import streamlit as st
import numpy as np
import pandas as pd
import json

st.set_page_config(page_title="パチスロ設定推測アプリ", layout="wide", initial_sidebar_state="expanded")

# --- カスタムCSS（数値入力欄の+-ボタン非表示） ---
st.markdown("""
    <style>
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; 
        margin: 0; 
    }
    input[type=number] {
        -moz-appearance: textfield;
    }
    </style>
""", unsafe_allow_html=True)

# --- 状態更新用コールバック関数 ---
def add_val(key, val):
    st.session_state[key] += val

def sub_val(key, val):
    st.session_state[key] = max(0, st.session_state[key] - val)

def reset_counts():
    """現在のカウントとゲーム数だけを0にリセットする"""
    st.session_state.input_total_games = 0
    for i in range(1, 4):
        st.session_state[f'input_p1_{i}'] = 0
        for j in range(1, 21):
            st.session_state[f'input_p2_{i}_{j}'] = 0
    st.session_state.result_df = None

# --- セッションステートの初期化 ---
def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

init_state('model_name', "")
init_state('eval_level', 3)
init_state('input_total_games', 0)
init_state('result_df', None)

for i in range(1, 4):
    init_state(f'name_e{i}', f"要素{i}")
    init_state(f'type_e{i}', "パターン①：小役とゲーム数")
    init_state(f'num_items_e{i}', 2)
    init_state(f'input_p1_{i}', 0)
    for s in range(1, 7):
        init_state(f'p1_e{i}_s{s}', 100.0)
    for j in range(1, 21):
        init_state(f'p2_e{i}_name{j}', f"項目{j}")
        init_state(f'input_p2_{i}_{j}', 0)
        for s in range(1, 7):
            init_state(f'p2_e{i}_item{j}_s{s}', 25.0)

# --- エクスポート用キーの定義 ---
export_keys = ['model_name', 'eval_level', 'input_total_games']
for i in range(1, 4):
    export_keys.extend([f'name_e{i}', f'type_e{i}', f'num_items_e{i}', f'input_p1_{i}'])
    for s in range(1, 7):
        export_keys.append(f'p1_e{i}_s{s}')
    for j in range(1, 21):
        export_keys.extend([f'p2_e{i}_name{j}', f'input_p2_{i}_{j}'])
        for s in range(1, 7):
            export_keys.append(f'p2_e{i}_item{j}_s{s}')

# --- 関数：事前確率（環境要因）の計算 ---
def get_prior_distribution(evaluation_level):
    confidences = {1: 0.10, 2: 0.275, 3: 0.450, 4: 0.625, 5: 0.80}
    p_high = confidences[evaluation_level]
    p_low = 1.0 - p_high
    ratio_low = np.array([0.50, 0.30, 0.20])
    ratio_high = np.array([0.30, 0.30, 0.40])
    prior = np.zeros(6)
    prior[0:3] = p_low * ratio_low
    prior[3:6] = p_high * ratio_high
    return prior

# ==========================================
# サイドバー構築
# ==========================================
st.sidebar.title("⚙️ 設定管理と推測要素")

# 1. JSONファイルの読み込み（一番上）
st.sidebar.header("📁 機種データ(JSON)の読み込み")
uploaded_file = st.sidebar.file_uploader("JSONファイルを選択して状態を復元", type="json")
if uploaded_file is not None:
    file_content = uploaded_file.getvalue()
    # 同じファイルが再読込ループになるのを防ぐ
    if st.session_state.get('last_uploaded') != file_content:
        st.session_state['last_uploaded'] = file_content
        try:
            data = json.loads(file_content.decode('utf-8'))
            for k, v in data.items():
                if k in st.session_state:
                    st.session_state[k] = v
            # 読み込み時は計算結果を一旦リセットする
            st.session_state.result_df = None
            st.rerun()
        except Exception as e:
            st.sidebar.error("読み込みに失敗しました。")

# 2. 現在のデータの保存
st.sidebar.markdown("---")
st.sidebar.header("💾 現在の状態を保存")
st.sidebar.text_input("機種名 (ファイル名用)", key="model_name", placeholder="例：マイジャグラーV")
model_name = st.session_state.model_name
file_name = f"{model_name}.json" if model_name else "パチスロ設定データ.json"

export_data = {k: st.session_state[k] for k in export_keys if k in st.session_state}
json_string = json.dumps(export_data, ensure_ascii=False, indent=2)

st.sidebar.download_button(
    label="現在の設定とカウントを保存",
    data=json_string,
    file_name=file_name,
    mime="application/json",
    use_container_width=True
)

st.sidebar.markdown("---")

# 3. 推測要素の詳細設定
st.sidebar.header("🔧 推測要素の各種設定")
for i in range(1, 4):
    with st.sidebar.expander(f"推測要素 {i}", expanded=(i==1)):
        st.text_input(f"要素{i}の名称", key=f"name_e{i}")
        e_type = st.radio(
            "カウントのタイプ", 
            ["パターン①：小役とゲーム数", "パターン②：抽選結果（振り分け）"], 
            key=f"type_e{i}"
        )
        
        if "パターン①" in e_type:
            st.caption("各設定の確率を分母(1/X)で入力してください。")
            for s in range(1, 7):
                st.number_input(f"設定{s}の分母", min_value=0.0, step=1.0, key=f"p1_e{i}_s{s}")
        else:
            st.caption("項目ごとの振り分け(%)を入力。（最大20項目）")
            num_items = st.selectbox("項目の数", list(range(2, 21)), key=f"num_items_e{i}")
            for j in range(1, num_items + 1):
                st.markdown(f"**項目 {j}**")
                st.text_input("名称", key=f"p2_e{i}_name{j}")
                col_a, col_b = st.columns(2)
                for s in range(1, 7):
                    target_col = col_a if s <= 3 else col_b
                    with target_col:
                        st.number_input(f"設定{s}(%)", min_value=0.0, max_value=100.0, step=1.0, key=f"p2_e{i}_item{j}_s{s}")


# ==========================================
# メイン画面構築
# ==========================================
if model_name:
    st.title(f"🎰 パチスロ設定推測：{model_name}")
else:
    st.title("🎰 パチスロ設定推測アプリ")

# 1. 周りの台の状況
st.header("1. 周りの台の状況（環境要因）")
eval_level = st.slider(
    "周りの台の状況を5段階で評価してください（1:最悪 〜 5:最高）", 
    min_value=1, max_value=5, step=1, key="eval_level"
)
confidences_str = {1: "10%", 2: "27.5%", 3: "45%", 4: "62.5%", 5: "80%"}
st.info(f"現在の高設定(4,5,6)の自信度: **{confidences_str[eval_level]}**")
prior_prob = get_prior_distribution(eval_level)


# 2. 自分の台のデータ入力
st.header("2. 自分の台のデータ入力")

# カウントリセットボタン
col_r1, col_r2 = st.columns([1, 2])
with col_r1:
    st.button("🗑️ 現在のカウントを全て0にする", on_click=reset_counts, use_container_width=True)

st.markdown("---")

# 共通ゲーム数入力
st.markdown("##### 共通ゲーム数")
st.number_input("共通ゲーム数", min_value=0, key="input_total_games", label_visibility="collapsed")
col_g1, col_g2, col_g3 = st.columns(3)
with col_g1:
    st.button("+10", use_container_width=True, on_click=add_val, args=("input_total_games", 10))
with col_g2:
    st.button("+100", use_container_width=True, on_click=add_val, args=("input_total_games", 100))
with col_g3:
    st.button("+1000", use_container_width=True, on_click=add_val, args=("input_total_games", 1000))

st.markdown("---")

# 各要素のカウントUI (全て縦に並べる)
for i in range(1, 4):
    name_val = st.session_state[f'name_e{i}']
    st.subheader(f"■ {name_val}")
    
    if "パターン①" in st.session_state[f'type_e{i}']:
        st.caption("共通ゲーム数を参照します")
        count_key = f'input_p1_{i}'
        
        st.number_input("カウント", min_value=0, key=count_key, label_visibility="collapsed")
        c1, c2 = st.columns(2)
        with c1:
            st.button("-1", key=f"btn_m_p1_{i}", use_container_width=True, on_click=sub_val, args=(count_key, 1))
        with c2:
            st.button("+1", key=f"btn_p_p1_{i}", type="primary", use_container_width=True, on_click=add_val, args=(count_key, 1))

    else:
        st.caption("各項目の発生回数をカウントします")
        num_items = st.session_state[f'num_items_e{i}']
        
        for j in range(1, num_items + 1):
            item_name = st.session_state[f'p2_e{i}_name{j}']
            count_key = f'input_p2_{i}_{j}'
            
            st.markdown(f"**{item_name}**")
            st.number_input("回数", min_value=0, key=count_key, label_visibility="collapsed")
            c1, c2 = st.columns(2)
            with c1:
                st.button("-1", key=f"btn_m_p2_{i}_{j}", use_container_width=True, on_click=sub_val, args=(count_key, 1))
            with c2:
                st.button("+1", key=f"btn_p_p2_{i}_{j}", type="primary", use_container_width=True, on_click=add_val, args=(count_key, 1))
                
    st.markdown("---")

# ==========================================
# 3. 推測結果の計算と表示
# ==========================================
if st.button("🔄 設定推測を計算・更新する", type="primary", use_container_width=True):
    log_likelihood_total = np.zeros(6)
    
    for i in range(1, 4):
        if "パターン①" in st.session_state[f'type_e{i}']:
            k = st.session_state[f'input_p1_{i}']
            n = st.session_state.input_total_games
            probs_denom = [st.session_state[f'p1_e{i}_s{s}'] for s in range(1, 7)]
            probs = np.array([1.0 / val if val > 0 else 0 for val in probs_denom])
            
            if n >= k and n > 0:
                epsilon = 1e-10
                p_safe = np.clip(probs, epsilon, 1 - epsilon)
                ll = k * np.log(p_safe) + (n - k) * np.log(1 - p_safe)
                log_likelihood_total += ll
        else:
            num_items = st.session_state[f'num_items_e{i}']
            total_k = 0
            k_list = []
            p_list = []
            for j in range(1, num_items + 1):
                count_key = f'input_p2_{i}_{j}'
                k_list.append(st.session_state[count_key])
                p_list.append([st.session_state[f'p2_e{i}_item{j}_s{s}'] / 100.0 for s in range(1, 7)])
                total_k += st.session_state[count_key]
                
            if total_k > 0:
                epsilon = 1e-10
                for j in range(num_items):
                    k_val = k_list[j]
                    p_safe = np.clip(p_list[j], epsilon, 1.0)
                    ll = k_val * np.log(p_safe)
                    log_likelihood_total += ll

    max_ll = np.max(log_likelihood_total)
    likelihood_scaled = np.exp(log_likelihood_total - max_ll)
    unnormalized_posterior = likelihood_scaled * prior_prob

    if np.sum(unnormalized_posterior) > 0:
        posterior_prob = unnormalized_posterior / np.sum(unnormalized_posterior)
    else:
        posterior_prob = prior_prob

    settings = ["設定1", "設定2", "設定3", "設定4", "設定5", "設定6"]
    st.session_state.result_df = pd.DataFrame({
        "設定": settings,
        "確率(%)": posterior_prob * 100
    })

if st.session_state.result_df is not None:
    st.header("3. 設定推測結果")
    
    col_dummy1, col_table, col_dummy2 = st.columns([1, 2, 1])
    with col_table:
        st.dataframe(
            st.session_state.result_df.style.format({"確率(%)": "{:.2f}%"})
                     .background_gradient(cmap='Blues', subset=['確率(%)']),
            hide_index=True,
            use_container_width=True
        )
