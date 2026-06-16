import streamlit as st
import os
from datetime import datetime, timedelta
from utils.database import (
    init_db,
    add_item,
    get_all_items,
    delete_item,
    get_shopping_suggestions,
)
from utils.notification import save_config, _get_config, send_email
from utils.auth import register_user, login_user

st.set_page_config(page_title="Food Shelf Life Tracker", page_icon="🥗", layout="wide")

# 自定义 CSS - 暖色系设计
st.markdown(
    """
<style>
    /* 全局 */
    .stApp { background: #fdf6f0; }
    .main > div { padding: 1.5rem 2rem; }

    /* 标题 */
    h1, h2, h3 { color: #2d1810; }

    /* 卡片 */
    .food-card {
        background: white;
        color: #2d1810;
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-bottom: 1rem;
        border-left: 5px solid #4caf50;
        transition: transform 0.15s;
    }
    .food-card:hover { transform: translateY(-2px); }
    .food-card.expiring {
        border-left-color: #ff9800;
        background: #fff8e1;
        color: #5d3a00;
    }
    .food-card.expired {
        border-left-color: #f44336;
        background: #ffebee;
        color: #b71c1c;
    }

    /* 徽标 */
    .badge {
        display: inline-block;
        padding: 0.15rem 0.7rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-green { background: #e8f5e9; color: #2e7d32; }
    .badge-orange { background: #fff3e0; color: #e65100; }
    .badge-red { background: #ffebee; color: #c62828; }

    /* 提醒横幅 */
    .alert-banner {
        background: linear-gradient(135deg, #fff3e0, #ffe0b2);
        border: 1px solid #ffb74d;
        border-radius: 12px;
        padding: 0.8rem 1.2rem;
        margin-bottom: 1.5rem;
        font-weight: 500;
        color: #e65100;
    }

    /* 全局文字颜色 */
    body, .stMarkdown, p, li, span, div:not(.stButton) { color: #2d1810; }

    /* 录入区卡片 */
    .input-card {
        background: white;
        color: #2d1810;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }

    /* 分割线 */
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2d1810;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #f0e0d0;
    }

    /* 购物建议卡片 */
    .suggestion-category {
        background: white;
        color: #2d1810;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 6px rgba(0,0,0,0.05);
    }
    .suggestion-category h4 { margin: 0 0 0.5rem 0; color: #2d1810; }
    .suggestion-item {
        padding: 0.3rem 0;
        color: #555;
        font-size: 0.95rem;
    }

    /* Streamlit 原生微调 */
    .stButton > button {
        border-radius: 10px;
        font-weight: 500;
    }
    .stTextInput > div > div > input { border-radius: 10px; }
    .stSelectbox > div > div > select { border-radius: 10px; }
    .stDateInput > div > div > input { border-radius: 10px; }
    .stNumberInput > div > div > input { border-radius: 10px; }
</style>
""",
    unsafe_allow_html=True,
)

# 初始化数据库
init_db()

# ========== 用户登录 / 注册 ==========
if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None

if not st.session_state.user_id:
    st.markdown("""
    <div style="max-width:400px;margin:3rem auto;text-align:center;">
        <h1 style="font-size:3rem;margin-bottom:0;">🥗</h1>
        <h2 style="color:#2d1810;">Food Shelf Life Tracker</h2>
        <p style="color:#8d6e63;">登录后开始追踪食品保质期</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔑 登录", "📝 注册"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="输入用户名")
            password = st.text_input("密码", type="password", placeholder="输入密码")
            if st.form_submit_button("登录", type="primary", use_container_width=True):
                ok, msg, uid = login_user(username, password)
                if ok:
                    st.session_state.user_id = uid
                    st.session_state.username = username.strip()
                    st.rerun()
                else:
                    st.error(msg)

    with tab_register:
        with st.form("register_form"):
            new_user = st.text_input("用户名", placeholder="至少2个字符，支持中文")
            new_pwd = st.text_input("密码", type="password", placeholder="至少4个字符")
            if st.form_submit_button("注册", use_container_width=True):
                ok, msg = register_user(new_user, new_pwd)
                if ok:
                    st.success(msg + "，请切换到登录页登录")
                else:
                    st.error(msg)

    st.stop()

# ========== 侧边栏 - 用户信息 & 邮箱配置 ==========
with st.sidebar:
    st.markdown(f"👋 欢迎，**{st.session_state.username}**")
    if st.button("🚪 退出登录"):
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()
    st.markdown("---")
    st.markdown("### � 邮件提醒设置")

    mail_config = _get_config()
    configured = bool(mail_config["sender"] and mail_config["password"])

    if configured:
        st.markdown(f"""\
<div style="background:#e8f5e9;border-radius:10px;padding:0.6rem 1rem;font-size:0.8rem;color:#2e7d32;">
✅ 邮箱已配置<br>发件: {mail_config['sender']}<br>收件: {mail_config['recipient']}
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""\
<div style="background:#fff3e0;border-radius:10px;padding:0.6rem 1rem;font-size:0.8rem;color:#e65100;">
⚠️ 未设置邮箱，无法发送提醒
</div>""", unsafe_allow_html=True)

    with st.expander("⚙️ 配置邮箱"):
        sender = st.text_input("发件邮箱", value=mail_config.get("sender", ""),
                               placeholder="example@qq.com / example@163.com")
        password = st.text_input("邮箱授权码", type="password", value=mail_config.get("password", ""),
                                 placeholder="开启SMTP服务获取授权码")
        recipient = st.text_input("收件邮箱", value=mail_config.get("recipient", ""),
                                  placeholder="接收提醒的邮箱")

        if st.button("💾 保存配置", use_container_width=True):
            save_config(sender, password, recipient)
            st.success("✅ 配置已保存！")
            st.rerun()

    # 邮件测试
    if configured:
        if st.button("📨 发送测试邮件", use_container_width=True):
            with st.spinner("发送中..."):
                ok, err = send_email("🥗 测试邮件", "<h2>邮箱配置成功！</h2><p>以后每天会收到食物保质期提醒邮件。</p>")
                if ok:
                    st.success("✅ 测试邮件已发送，请查收！")
                else:
                    st.error(f"❌ 发送失败：{err}")

    st.markdown("---")
    st.markdown("""\
<div style="font-size:0.75rem;color:#999;line-height:1.6;">
📌 <b>获取邮箱授权码</b><br><br>
<b>QQ邮箱：</b><br>
1. 登录 QQ邮箱 → 设置 → 账户<br>
2. 开启 "POP3/SMTP服务"<br>
3. 生成授权码<br><br>
<b>163邮箱：</b><br>
1. 登录 163邮箱 → 设置 → POP3/SMTP<br>
2. 开启 "POP3/SMTP服务"<br>
3. 生成授权码
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""\
<div style="font-size:0.75rem;color:#bbb;text-align:center;">
☁️ 部署到云端后，在 Streamlit Secrets 设置：<br>
<code>MAIL_SENDER</code><br>
<code>MAIL_PASSWORD</code><br>
<code>MAIL_RECIPIENT</code><br>
<code>DATABASE_URL</code><br>
（邮箱服务商自动识别）
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div style='font-size:0.8rem;color:#aaa;text-align:center;'>Food Shelf Life Tracker v1.0</div>", unsafe_allow_html=True)

# ========== 顶部标题 ==========
col_logo, col_title = st.columns([0.06, 1])
with col_logo:
    st.markdown("<h1 style='font-size:2.2rem;margin:0;'>🥗</h1>", unsafe_allow_html=True)
with col_title:
    st.markdown("<h1 style='margin:0;'>Food Shelf Life Tracker</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#8d6e63;margin-top:-0.3rem;'>追踪保质期 · 拒绝浪费</p>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ========== 检查即将过期商品，显示提醒横幅 ==========
today = datetime.today().strftime("%Y-%m-%d")
all_items = get_all_items(st.session_state.user_id)
expiring_soon = [
    it for it in all_items
    if it["expire_date"] >= today
    and (datetime.strptime(it["expire_date"], "%Y-%m-%d") - datetime.today()).days <= 5
]
expired_items = [it for it in all_items if it["expire_date"] < today]
expiring_count = len(expiring_soon)
expired_count = len(expired_items)

if expiring_count > 0:
    msg = "⏰ 有 {} 件商品即将过期，记得及时处理！".format(expiring_count)
    if expired_count > 0:
        msg += f" 还有 {expired_count} 件已过期，快去生成购物建议吧！"
    st.markdown(
        f'<div class="alert-banner">{msg}</div>', unsafe_allow_html=True
    )

# ========== Tab 布局 ==========
tab1, tab2, tab3 = st.tabs(["📦 录入商品", "📋 食品清单", "🛒 购物建议"])

# ==================== TAB 1: 录入 ====================
with tab1:
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.markdown("### ✏️ 添加新商品")

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("商品名称", placeholder="例如：鲜牛奶、鸡胸肉...")
        category = st.selectbox(
            "分类", ["乳制品", "肉类", "蔬菜", "饮料", "水果", "调味品", "零食", "其他"]
        )

    with col2:
        purchase_date = st.date_input(
            "购买日期", value=datetime.today()
        )
        shelf_life = st.number_input(
            "保质期（天）", min_value=1, max_value=3650, value=7, step=1
        )

    col_btn, _ = st.columns([0.3, 0.7])
    with col_btn:
        submitted = st.button("➕ 添加", type="primary", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("请输入商品名称")
        else:
            add_item(
                st.session_state.user_id,
                name.strip(),
                category,
                purchase_date.strftime("%Y-%m-%d"),
                shelf_life,
            )
            expire_date = purchase_date + timedelta(days=shelf_life)
            st.success(
                f"✅ 「{name.strip()}」已添加，到期日为 **{expire_date.strftime('%Y-%m-%d')}**"
            )
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ==================== TAB 2: 清单 ====================
with tab2:
    st.markdown(
        f'<div style="margin-bottom:1rem;color:#8d6e63;">共 {len(all_items)} 件商品 · 🟢 正常 · 🟡 即将过期 · 🔴 已过期</div>',
        unsafe_allow_html=True,
    )

    if not all_items:
        st.info("📭 还没有商品，去「录入商品」页面添加吧！")
    else:
        # 按状态分组
        normal_items = []
        for it in all_items:
            if it["expire_date"] < today:
                continue
            days_left = (datetime.strptime(it["expire_date"], "%Y-%m-%d") - datetime.today()).days
            if days_left > 5:
                normal_items.append(it)

        for item in all_items:
            days_left = (datetime.strptime(item["expire_date"], "%Y-%m-%d") - datetime.today()).days

            # 判断状态
            if days_left < 0:
                card_class = "food-card expired"
                badge = '<span class="badge badge-red">已过期</span>'
                days_text = f"已过期 {abs(days_left)} 天"
            elif days_left <= 3:
                card_class = "food-card expiring"
                badge = f'<span class="badge badge-orange">⏰ {days_left} 天</span>'
                days_text = f"还剩 {days_left} 天"
            elif days_left <= 5:
                card_class = "food-card expiring"
                badge = f'<span class="badge badge-orange">⚠️ {days_left} 天</span>'
                days_text = f"还剩 {days_left} 天"
            else:
                card_class = "food-card"
                badge = f'<span class="badge badge-green">✅ {days_left} 天</span>'
                days_text = f"还剩 {days_left} 天"

            with st.container():
                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                            <div>
                                <strong style="font-size:1.1rem;">{item['name']}</strong>
                                <span style="margin-left:0.6rem;font-size:0.8rem;color:white;font-weight:500;">{item['category']}</span>
                            </div>
                            <div style="display:flex;align-items:center;gap:0.5rem;">
                                {badge}
                            </div>
                        </div>
                        <div style="display:flex;gap:1.5rem;margin-top:0.4rem;font-size:0.85rem;color:#888;">
                            <span>🛒 购买日：{item['purchase_date']}</span>
                            <span>📅 到期日：{item['expire_date']}</span>
                            <span>⏳ {days_text}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # 删除按钮（放在卡片下方）
                col_del, _ = st.columns([0.1, 0.9])
                with col_del:
                    if st.button(f"🗑️ 删除", key=f"del_{item['id']}"):
                        delete_item(item["id"])
                        st.rerun()

# ==================== TAB 3: 购物建议 ====================
with tab3:
    st.markdown("### 🛒 一键购物建议")
    st.markdown(
        '<p style="color:#8d6e63;">基于已过期和即将过期（3天内）的商品自动生成</p>',
        unsafe_allow_html=True,
    )

    suggestions = get_shopping_suggestions(st.session_state.user_id)

    if not suggestions:
        st.success("🎉 所有商品都很新鲜，暂时不需要购物！")
    else:
        # 按分类汇总
        from collections import defaultdict

        cat_map = defaultdict(list)
        for item in suggestions:
            cat_map[item["category"]].append(item)

        total = len(suggestions)
        st.markdown(
            f'<div class="alert-banner">🛍️ 共 {total} 件商品需要补充，快去采购吧！</div>',
            unsafe_allow_html=True,
        )

        for cat, items in sorted(cat_map.items()):
            with st.container():
                items_html = ""
                for it in items:
                    status = "🔴 已过期" if it["expire_date"] < today else "⏰ 即将过期"
                    items_html += f'<div class="suggestion-item">• <strong>{it["name"]}</strong> — {status}（{it["expire_date"]}）</div>'

                st.markdown(
                    f"""
                    <div class="suggestion-category">
                        <h4>📂 {cat}（{len(items)} 件）</h4>
                        {items_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # 一键复制
        text_lines = ["🛒 购物清单", "=" * 20]
        for cat, items in sorted(cat_map.items()):
            text_lines.append(f"\n【{cat}】")
            for it in items:
                text_lines.append(f"  · {it['name']}")
        text_lines.append(f"\n{'=' * 20}")
        text_lines.append(f"共 {total} 件商品需要补充")

        copy_text = "\n".join(text_lines)
        st.text_area(
            "📋 可复制的购物清单",
            value=copy_text,
            height=200,
            help="选中全部内容后复制，发送给家人或贴到冰箱上",
        )