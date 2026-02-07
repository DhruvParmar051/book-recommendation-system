import os
import streamlit as st
import requests
import ast
import math

# ======================================================
# CONFIG
# ======================================================

API_BASE = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000"  # fallback for local dev
)

PAGE_SIZE = 5
RECOMMEND_PAGE_SIZE = 10

st.set_page_config(
    page_title="📚 Book Recommender",
    layout="wide"
)

# ======================================================
# STYLES
# ======================================================

st.markdown("""
<style>
.book-title {
    font-size: 26px;
    font-weight: 700;
}
.section-title {
    font-size: 22px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# HELPERS
# ======================================================

def parse_list(value):
    if not value:
        return None
    if isinstance(value, list):
        return ", ".join(value)
    if isinstance(value, str):
        try:
            v = ast.literal_eval(value)
            if isinstance(v, list):
                return ", ".join(v)
        except Exception:
            return value
    return value


def show_field(label, value):
    st.markdown(f"**{label}:** {value if value else '_Not available_'}")


def get_books(skip, limit, search_field=None, query=None):
    try:
        params = {"skip": skip, "limit": limit}
        if search_field and query:
            params["search_field"] = search_field
            params["query"] = query

        r = requests.get(f"{API_BASE}/books/", params=params, timeout=20)
        r.raise_for_status()
        return r.json()

    except requests.RequestException:
        st.error("❌ Cannot connect to backend API")
        return {"items": [], "total": 0}


@st.cache_data(ttl=300)
def get_recommendations(query, top_k):
    try:
        r = requests.post(
            f"{API_BASE}/recommend",
            json={"query": query, "top_k": top_k},
            timeout=60
        )

        if r.status_code == 503:
            return {"error": "Recommendation engine is warming up. Please try again shortly."}

        r.raise_for_status()
        return r.json()

    except requests.RequestException:
        return {"error": "Unable to connect to recommendation service."}


@st.cache_data(show_spinner=True)
def get_cover(isbn):
    if not isbn:
        return None
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"

# ======================================================
# SIDEBAR NAVIGATION
# ======================================================

if "page" not in st.session_state:
    st.session_state.page = "Browse"

st.sidebar.title("📘 Book Recommender")

if st.sidebar.button("📚 Browse Books"):
    st.session_state.page = "Browse"

if st.sidebar.button("🤖 Get Recommendations"):
    st.session_state.page = "Recommend"

# ======================================================
# PAGE 1 — BROWSE BOOKS
# ======================================================

if st.session_state.page == "Browse":
    st.title("📚 Browse Library")

    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "Search books",
            placeholder="Enter keyword (e.g. machine, data, python)",
            label_visibility="collapsed"
        )
    with col2:
        search_field = st.selectbox(
            "Search field",
            ["title", "authors", "publisher"],
            label_visibility="collapsed"
        )

    if "skip" not in st.session_state:
        st.session_state.skip = 0

    with st.spinner("Loading books…"):
        data = get_books(
            st.session_state.skip,
            PAGE_SIZE,
            search_field if search_query else None,
            search_query if search_query else None
        )

    books = data["items"]
    total = data["total"]
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    current_page = (st.session_state.skip // PAGE_SIZE) + 1

    if not books:
        st.info("No books found.")
    else:
        for book in books:
            with st.container(border=True):
                col_img, col_text = st.columns([1, 3], gap="large")

                with col_img:
                    cover = get_cover(book.get("isbn"))
                    if cover:
                        st.image(cover, use_container_width=True)
                    else:
                        st.markdown("🖼️ _No cover available_")

                with col_text:
                    st.markdown(
                        f"<div class='book-title'>{book.get('title','Untitled')}</div>",
                        unsafe_allow_html=True
                    )

                    show_field("Author", parse_list(book.get("authors")))
                    show_field("Publisher", book.get("publisher"))
                    show_field("Year", book.get("year"))
                    show_field("Subjects", parse_list(book.get("subjects")))

                    with st.expander("📖 Read full summary"):
                        st.write(book.get("summary") or "_Summary not available_")

    col_prev, col_mid, col_next = st.columns([1, 5, 1])

    with col_prev:
        if st.button("⬅ Previous", disabled=current_page == 1):
            st.session_state.skip -= PAGE_SIZE
            st.rerun()

    with col_mid:
        st.markdown(
            f"<p style='text-align:center;'>"
            f"Page <b>{current_page}</b> of <b>{total_pages}</b> "
            f"({total} books)</p>",
            unsafe_allow_html=True
        )

    with col_next:
        if st.button("Next ➡", disabled=current_page >= total_pages):
            st.session_state.skip += PAGE_SIZE
            st.rerun()

# ======================================================
# PAGE 2 — RECOMMENDATIONS
# ======================================================

else:
    st.title("🤖 Book Recommendations")

    st.markdown(
        "<div class='section-title'>Describe the book you are looking for</div>",
        unsafe_allow_html=True
    )

    query = st.text_area(
        "Book description",
        placeholder="Example: A book about machine learning and data mining",
        height=70,
        label_visibility="collapsed"
    )

    top_k_input = st.text_input(
        "Number of recommendations",
        value="5",
        label_visibility="collapsed"
    )

    try:
        top_k = max(1, int(top_k_input))
    except ValueError:
        top_k = 5

    if "rec_page" not in st.session_state:
        st.session_state.rec_page = 1

    if st.button("✨ Recommend Books"):
        if not query.strip():
            st.warning("Please enter a description.")
        else:
            with st.spinner("Finding the best matches…"):
                st.session_state.rec_results = get_recommendations(query, top_k)
                st.session_state.rec_page = 1

    results = st.session_state.get("rec_results")

    if isinstance(results, dict) and "error" in results:
        st.warning(results["error"])
        st.stop()

    if not results:
        st.info("No recommendations found.")
        st.stop()

    total = len(results)
    page_size = min(RECOMMEND_PAGE_SIZE, total)
    total_pages = math.ceil(total / page_size)
    page = st.session_state.rec_page

    start = (page - 1) * page_size
    end = start + page_size
    page_items = results[start:end]

    for book in page_items:
        with st.container(border=True):
            col_img, col_text = st.columns([1, 3], gap="large")

            with col_img:
                cover = get_cover(book.get("isbn"))
                if cover:
                    st.image(cover, use_container_width=True)
                else:
                    st.markdown("🖼️ _No cover available_")

            with col_text:
                st.markdown(
                    f"<div class='book-title'>{book.get('title','Untitled')}</div>",
                    unsafe_allow_html=True
                )

                show_field("Author", parse_list(book.get("authors")))
                show_field("Publisher", book.get("publisher"))
                show_field("Year", book.get("year"))
                show_field("Subjects", parse_list(book.get("subjects")))

                with st.expander("📖 Read full summary"):
                    st.write(book.get("summary") or "_Summary not available_")

    if total_pages > 1:
        col_prev, col_mid, col_next = st.columns([1, 5, 1])

        with col_prev:
            if st.button("⬅ Previous", disabled=page == 1):
                st.session_state.rec_page -= 1
                st.rerun()

        with col_mid:
            st.markdown(
                f"<p style='text-align:center;'>"
                f"Page <b>{page}</b> of <b>{total_pages}</b> "
                f"({total} recommendations)</p>",
                unsafe_allow_html=True
            )

        with col_next:
            if st.button("Next ➡", disabled=page == total_pages):
                st.session_state.rec_page += 1
                st.rerun()
