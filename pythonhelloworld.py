import streamlit as st
import numpy as np
import pandas as pd

# ==========================================
# 🔧 【設定エリア】機種の理論値をハードコーディング
# ==========================================
# ここを書き換えるだけで、別の機種のアプリが作れます。

MACHINE_NAME = "カバネリ海門"

# 推測要素のリスト
# "type" を "koyaku" (ゲーム数参照) か "furiwake" (回数振り分け) のどちらかにします。
ELEMENTS = [
    {
        "type": "koyaku",
        "name": "共通ベル",
        "probs": [121.1, 114.4, 112.8, 106.2, 104.2, 99.1]  # 設定1〜6の分母(1/X)
    },

    {
        "type": "furiwake",
        "name": "ボーナス終了画面",
        "items": [
            {"name": "デフォルト", "probs": [97.7, 97.7, 97.7, 95, 93, 86.8]}, # 設定1〜6の振り分け(%)
            {"name": "高設定示唆", "probs": [2.3, 2.3, 2.3, 5, 7, 10]},
            {"name": "設定6確定",  "probs": [ 0,  0,  0, 0, 0, 3.2]}
        ]
    },

    {
        "type": "furiwake",
        "name": "ボイス",
        "items": [
            {"name": "男性", "probs": [50, 37.35, 50, 37, 47, 34.3]}, # 設定1〜6の振り分け(%)
            {"name": "女性", "probs": [37.65, 50, 37.35, 47, 35.55, 47]}, # 設定1〜6の振り分け(%)
            {"name": "高設定示唆弱", "probs": [11, 11, 11, 14, 15, 16]},
            {"name": "高設定示唆中", "probs": [1.3, 1.3, 1.3, 1.6, 1.8, 2]},
            {"name": "高設定示唆今日", "probs": [0.05, 0.05, 0.05, 0.1, 0.15, 0.2]},
            {"name": "設定2以上",  "probs": [ 0, 0.3, 0.3, 0.3, 0.3, 0.3]},
            {"name": "設定6確定",  "probs": [ 0, 0, 0, 0, 0.2, 0.2]}
        ]
    },

    {
        "type": "furiwake",
        "name": "駿城単チャメ",
        "items": [
            {"name": "1000Pts", "probs": [98.8, 98, 98, 98, 98, 97.7]}, # 設定1〜6の振り分け(%)
            {"name": "3000Pts", "probs": [1.2, 2, 2, 2, 2, 2.3]}
        ]
    },

    {
        "type": "furiwake",
        "name": "単チャメ発光",
        "items": [
            {"name": "非発光", "probs": [88, 88, 88, 84, 83, 82]}, # 設定1〜6の振り分け(%)
            {"name": "発光", "probs": [12, 12, 12, 16, 17, 18]}
        ]
    },
    {
        "type": "furiwake",
        "name": "駆け抜け12通常3周期当選",
        "items": [
            {"name": "非当選", "probs": [83, 83, 83, 73, 70, 65]}, # 設定1〜6の振り分け(%)
            {"name": "当選", "probs": [17, 17, 17, 27, 30, 35]}
        ]
    },
    {
        "type": "furiwake",
        "name": "駆け抜け3通常12周期当選",
        "items": [
            {"name": "非当選", "probs": [70, 70, 70, 60, 55, 50]}, # 設定1〜6の振り分け(%)
            {"name": "当選", "probs": [30, 30, 30, 40, 45, 50]}
        ]
    }
    
]

# ==========================================


st.set_page_config(page_title=f"設定推測：{MACHINE_NAME}", layout="wide")

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
    st.session_state.total_games = 0
    for i, elem in enumerate(ELEMENTS):
        if elem["type"] == "koyaku":
            st.session_state[f"count_koyaku_{i}"] = 0
        elif elem["type"] == "furiwake":
            for j in range(len(elem["items"])):
                st.session_state[f"count_furiwake_{i}_{j}"] = 0
    st.session_state.result_df = None

# --- セッションステートの初期化 ---
if "total_games" not in st.session_state:
    st.session_state.total_games = 0
if "result_df" not in st.session_state:
    st.session_state.result_df = None

for i, elem in enumerate(ELEMENTS):
    if elem["type"] == "koyaku":
        if f"count_koyaku_{i}" not in st.session_state:
            st.session_state[f"count_koyaku_{i}"] = 0
    elif elem["type"] == "furiwake":
        for j in range(len(elem["items"])):
            if f"count_furiwake_{i}_{j}" not in st.session_state:
                st.session_state[f"count_furiwake_{i}_{j}"] = 0


# --- 関数：事前確率（環境要因）の計算 ---
def get_prior_distribution(evaluation_level):
    confidences = {1: 0.10, 2: 0.275, 3: 0.450, 4: 0.625, 5: 0.80}
    p_high = confidences[evaluation_level]
    p_low = 1.0 - p_high
    ratio_low = np.array([0.60, 0.40, 0])
    ratio_high = np.array([0.60, 0.25, 0.15])
    prior = np.zeros(6)
    prior[0:3] = p_low * ratio_low
    prior[3:6] = p_high * ratio_high
    return prior

# ==========================================
# メイン画面構築
# ==========================================
st.title(f"🎰 パチスロ設定推測：{MACHINE_NAME}")

# 1. 周りの台の状況
st.header("1. 周りの台の状況（環境要因）")
eval_level = st.slider(
    "周りの台の状況を5段階で評価してください（1:最悪 〜 5:最高）", 
    min_value=1, max_value=5, value=3, step=1, key="eval_level"
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
st.number_input("共通ゲーム数", min_value=0, key="total_games", label_visibility="collapsed")
col_g1, col_g2, col_g3 = st.columns(3)
with col_g1:
    st.button("+10", use_container_width=True, on_click=add_val, args=("total_games", 10))
with col_g2:
    st.button("+100", use_container_width=True, on_click=add_val, args=("total_games", 100))
with col_g3:
    st.button("+1000", use_container_width=True, on_click=add_val, args=("total_games", 1000))

st.markdown("---")

# 各要素のカウントUI (設定エリアのリストに基づいて自動生成)
for i, elem in enumerate(ELEMENTS):
    st.subheader(f"■ {elem['name']}")
    
    if elem["type"] == "koyaku":
        st.caption(f"共通ゲーム数を参照します (理論値: 設定1=1/{elem['probs'][0]} 〜 設定6=1/{elem['probs'][5]})")
        count_key = f"count_koyaku_{i}"
        
        st.number_input("カウント", min_value=0, key=count_key, label_visibility="collapsed")
        c1, c2 = st.columns(2)
        with c1:
            st.button("-1", key=f"btn_m_k_{i}", use_container_width=True, on_click=sub_val, args=(count_key, 1))
        with c2:
            st.button("+1", key=f"btn_p_k_{i}", type="primary", use_container_width=True, on_click=add_val, args=(count_key, 1))

    elif elem["type"] == "furiwake":
        st.caption("各項目の発生回数をカウントします")
        
        for j, item in enumerate(elem["items"]):
            count_key = f"count_furiwake_{i}_{j}"
            
            st.markdown(f"**{item['name']}**")
            st.number_input("回数", min_value=0, key=count_key, label_visibility="collapsed")
            c1, c2 = st.columns(2)
            with c1:
                st.button("-1", key=f"btn_m_f_{i}_{j}", use_container_width=True, on_click=sub_val, args=(count_key, 1))
            with c2:
                st.button("+1", key=f"btn_p_f_{i}_{j}", type="primary", use_container_width=True, on_click=add_val, args=(count_key, 1))
                
    st.markdown("---")


# ==========================================
# 3. 推測結果の計算と表示
# ==========================================
if st.button("🔄 設定推測を計算・更新する", type="primary", use_container_width=True):
    log_likelihood_total = np.zeros(6)
    
    # 尤度計算もリストに基づいて自動処理
    for i, elem in enumerate(ELEMENTS):
        if elem["type"] == "koyaku":
            k = st.session_state[f"count_koyaku_{i}"]
            n = st.session_state.total_games
            probs = np.array([1.0 / val if val > 0 else 0 for val in elem["probs"]])
            
            if n >= k and n > 0:
                epsilon = 1e-10
                p_safe = np.clip(probs, epsilon, 1 - epsilon)
                ll = k * np.log(p_safe) + (n - k) * np.log(1 - p_safe)
                log_likelihood_total += ll
                
        elif elem["type"] == "furiwake":
            total_k = 0
            k_list = []
            p_list = []
            for j, item in enumerate(elem["items"]):
                k_val = st.session_state[f"count_furiwake_{i}_{j}"]
                k_list.append(k_val)
                p_list.append([p / 100.0 for p in item["probs"]])
                total_k += k_val
                
            if total_k > 0:
                epsilon = 1e-10
                for j in range(len(elem["items"])):
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
