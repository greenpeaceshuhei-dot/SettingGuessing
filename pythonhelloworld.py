import streamlit as st
import numpy as np
import pandas as pd
import altair as alt

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

# --- セッションステートの初期化 ---
# 共通ゲーム数
if 'input_total_games' not in st.session_state:
    st.session_state.input_total_games = 0

# 各推測要素のカウントデータ（要素1〜3）
for i in range(1, 4):
    if f'input_p1_{i}' not in st.session_state:
        st.session_state[f'input_p1_{i}'] = 0  # パターン1用のカウント
    for j in range(1, 21): # パターン2用の項目1〜20のカウント
        if f'input_p2_{i}_{j}' not in st.session_state:
            st.session_state[f'input_p2_{i}_{j}'] = 0

# 推測結果の保存用
if 'result_df' not in st.session_state:
    st.session_state.result_df = None

# --- 関数：事前確率（環境要因）の計算 ---
def get_prior_distribution(evaluation_level):
    # 評価レベル(1〜5)に応じて高設定(設定4,5,6)の自信度を線形に変化 (10% 〜 80%)
    confidences = {1: 0.10, 2: 0.275, 3: 0.450, 4: 0.625, 5: 0.80}
    p_high = confidences[evaluation_level]
    p_low = 1.0 - p_high
    
    # 低設定内(1,2,3)、高設定内(4,5,6)での比率（一般的な配分を想定）
    ratio_low = np.array([0.60, 0.20, 0.01])
    ratio_high = np.array([0.10, 0.07, 0.02])
    
    prior = np.zeros(6)
    prior[0:3] = p_low * ratio_low
    prior[3:6] = p_high * ratio_high
    return prior

# --- サイドバー：推測要素の初期設定 ---
st.sidebar.title("⚙️ 推測要素の設定")
st.sidebar.markdown("各要素の「名前」「タイプ」「理論値」を設定します。")

elements_config = {}

for i in range(1, 4):
    with st.sidebar.expander(f"推測要素 {i}", expanded=(i==1)):
        name = st.text_input(f"要素{i}の名称", value=f"要素{i}", key=f"name_e{i}")
        e_type = st.radio(
            "カウントのタイプ", 
            ["パターン①：小役とゲーム数", "パターン②：抽選結果（振り分け）"], 
            key=f"type_e{i}"
        )
        
        config = {'name': name, 'type': e_type}
        
        if "パターン①" in e_type:
            st.caption("各設定の確率を分母(1/X)で入力してください。")
            probs = []
            for s in range(1, 7):
                # デフォルト値を適当に設定（1/100など）
                val = st.number_input(f"設定{s}の分母", value=100.0, step=1.0, key=f"p1_e{i}_s{s}")
                probs.append(1.0 / val if val > 0 else 0)
            config['probs'] = np.array(probs)
            
        else:
            st.caption("項目ごとの振り分け(%)を入力してください。（最大20項目）")
            num_items = st.selectbox("項目の数", list(range(2, 21)), index=1, key=f"num_items_e{i}")
            config['num_items'] = num_items
            config['items'] = []
            for j in range(1, num_items + 1):
                st.markdown(f"**項目 {j}**")
                item_name = st.text_input("名称", value=f"項目{j}", key=f"p2_e{i}_name{j}")
                item_probs = []
                # 2列でコンパクトに配置
                col_a, col_b = st.columns(2)
                for s in range(1, 7):
                    target_col = col_a if s <= 3 else col_b
                    with target_col:
                        val = st.number_input(f"設定{s}(%)", value=25.0, step=1.0, key=f"p2_e{i}_item{j}_s{s}")
                        item_probs.append(val / 100.0)
                config['items'].append({'name': item_name, 'probs': np.array(item_probs)})
                
        elements_config[i] = config

# --- メイン画面 ---
st.title("🎰 パチスロ設定推測アプリ")

# 1. 周りの状況（事前確率）
st.header("1. 周りの台の状況（環境要因）")
eval_level = st.slider(
    "周りの台の状況を5段階で評価してください（1:最悪 〜 5:最高）", 
    min_value=1, max_value=5, value=3, step=1
)
confidences_str = {1: "10%", 2: "27.5%", 3: "45%", 4: "62.5%", 5: "80%"}
st.info(f"現在の高設定(4,5,6)の自信度: **{confidences_str[eval_level]}**")
prior_prob = get_prior_distribution(eval_level)


# 2. 自分の台のデータ入力
st.header("2. 自分の台のデータ入力")

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

# 各要素のカウントUI
for i in range(1, 4):
    config = elements_config[i]
    st.subheader(f"■ {config['name']}")
    
    if "パターン①" in config['type']:
        # パターン1（小役など）の入力UI
        st.caption("共通ゲーム数を参照します")
        count_key = f'input_p1_{i}'
        
        st.number_input("カウント", min_value=0, key=count_key, label_visibility="collapsed")
        c1, c2 = st.columns(2)
        with c1:
            st.button("-1", key=f"btn_minus_{i}", use_container_width=True, on_click=sub_val, args=(count_key, 1))
        with c2:
            st.button("+1", key=f"btn_plus_{i}", type="primary", use_container_width=True, on_click=add_val, args=(count_key, 1))

    else:
        # パターン2（振り分け）の入力UI
        st.caption("各項目の発生回数をカウントします")
        num_items = config['num_items']
        items_config = config['items']
        
        for j in range(1, num_items + 1):
            item_name = items_config[j-1]['name']
            count_key = f'input_p2_{i}_{j}'
            
            st.markdown(f"**{item_name}**")
            st.number_input("回数", min_value=0, key=count_key, label_visibility="collapsed")
            c1, c2 = st.columns(2)
            with c1:
                st.button("-1", key=f"btn_m_{i}_{j}", use_container_width=True, on_click=sub_val, args=(count_key, 1))
            with c2:
                st.button("+1", key=f"btn_p_{i}_{j}", type="primary", use_container_width=True, on_click=add_val, args=(count_key, 1))
                
    st.markdown("---")


# --- 3. 推測結果の計算と表示 ---
st.markdown("---")

# 計算の実行ボタン
if st.button("🔄 設定推測を計算・更新する", type="primary", use_container_width=True):
    log_likelihood_total = np.zeros(6)
    
    # 各要素の対数尤度を合算
    for i in range(1, 4):
        config = elements_config[i]
        if "パターン①" in config['type']:
            k = st.session_state[f'input_p1_{i}']
            n = st.session_state.input_total_games
            probs = config['probs']
            if n >= k and n > 0:
                epsilon = 1e-10
                p_safe = np.clip(probs, epsilon, 1 - epsilon)
                ll = k * np.log(p_safe) + (n - k) * np.log(1 - p_safe)
                log_likelihood_total += ll
        else:
            num_items = config['num_items']
            items_config = config['items']
            total_k = 0
            k_list = []
            p_list = []
            for j in range(1, num_items + 1):
                count_key = f'input_p2_{i}_{j}'
                k_list.append(st.session_state[count_key])
                p_list.append(items_config[j-1]['probs'])
                total_k += st.session_state[count_key]
                
            if total_k > 0:
                epsilon = 1e-10
                for j in range(num_items):
                    k_val = k_list[j]
                    p_safe = np.clip(p_list[j], epsilon, 1.0)
                    ll = k_val * np.log(p_safe)
                    log_likelihood_total += ll

    # ベイズの定理による事後確率の計算
    max_ll = np.max(log_likelihood_total)
    likelihood_scaled = np.exp(log_likelihood_total - max_ll)
    unnormalized_posterior = likelihood_scaled * prior_prob

    if np.sum(unnormalized_posterior) > 0:
        posterior_prob = unnormalized_posterior / np.sum(unnormalized_posterior)
    else:
        posterior_prob = prior_prob

    # 結果をセッションステートに保存
    settings = ["設定1", "設定2", "設定3", "設定4", "設定5", "設定6"]
    st.session_state.result_df = pd.DataFrame({
        "設定": settings,
        "確率(%)": posterior_prob * 100
    })

# 結果が存在する場合のみ表示
if st.session_state.result_df is not None:
    st.header("3. 設定推測結果")
    
    col_dummy1, col_table, col_dummy2 = st.columns([1, 2, 1]) # 中央に配置
    with col_table:
        st.dataframe(
            st.session_state.result_df.style.format({"確率(%)": "{:.2f}%"})
                     .background_gradient(cmap='Blues', subset=['確率(%)']),
            hide_index=True,
            use_container_width=True
        )
