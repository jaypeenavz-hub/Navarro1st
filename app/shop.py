"""Catalogue browsing, search and product details."""

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for

from .db import get_db
from .services import login_required, paginate, wishlist_ids

bp = Blueprint("shop", __name__)

SORT_OPTIONS = {
    "featured": ("Recommended", "p.rating DESC, p.rating_count DESC"),
    "newest": ("Newest arrivals", "p.created_at DESC, p.id DESC"),
    "price-asc": ("Price: low to high", "p.price ASC"),
    "price-desc": ("Price: high to low", "p.price DESC"),
    "rating": ("Top rated", "p.rating DESC, p.rating_count DESC"),
    "name": ("Name: A to Z", "p.name ASC"),
}

BASE_SELECT = """SELECT p.*, c.name AS category_name, c.slug AS category_slug
                 FROM products p
                 LEFT JOIN categories c ON c.id = p.category_id"""


def _categories():
    return get_db().execute(
        """SELECT c.*, COUNT(p.id) AS product_count
           FROM categories c
           LEFT JOIN products p ON p.category_id = c.id AND p.is_active = 1
           GROUP BY c.id
           ORDER BY c.name"""
    ).fetchall()


@bp.route("/")
def home():
    db = get_db()
    featured = db.execute(
        BASE_SELECT + " WHERE p.is_active = 1 ORDER BY p.rating DESC, p.rating_count DESC LIMIT 8"
    ).fetchall()
    new_arrivals = db.execute(
        BASE_SELECT + " WHERE p.is_active = 1 ORDER BY p.id DESC LIMIT 4"
    ).fetchall()
    hero_products = db.execute(
        BASE_SELECT + " WHERE p.is_active = 1 AND c.slug IN ('laptops-tablets', 'monitors-displays', "
                      "'audio-headsets') ORDER BY p.rating DESC, p.rating_count DESC LIMIT 2"
    ).fetchall()
    categories = _categories()
    stats = {
        "products": db.execute("SELECT COUNT(*) AS total FROM products WHERE is_active = 1").fetchone()["total"],
        "categories": db.execute("SELECT COUNT(*) AS total FROM categories").fetchone()["total"],
        "orders": db.execute("SELECT COUNT(*) AS total FROM orders").fetchone()["total"],
    }
    return render_template(
        "shop/home.html",
        featured=featured,
        hero_products=hero_products,
        new_arrivals=new_arrivals,
        categories=categories,
        stats=stats,
        wishlist=wishlist_ids(g.user["id"] if g.user else None),
        active_category="",
        query="",
    )


@bp.route("/shop")
def products():
    db = get_db()
    query = request.args.get("q", "").strip()
    category_slug = request.args.get("category", "").strip()
    sort_key = request.args.get("sort", "featured")
    if sort_key not in SORT_OPTIONS:
        sort_key = "featured"
    min_rating = request.args.get("rating", "").strip()
    page = request.args.get("page", "1")
    page = int(page) if page.isdigit() else 1

    conditions = ["p.is_active = 1"]
    params = []
    if category_slug:
        conditions.append("c.slug = ?")
        params.append(category_slug)
    if query:
        conditions.append("(p.name LIKE ? OR p.description LIKE ? OR c.name LIKE ?)")
        like = f"%{query}%"
        params.extend([like, like, like])
    if min_rating in {"4", "3", "2"}:
        conditions.append("p.rating >= ?")
        params.append(float(min_rating))

    where = " WHERE " + " AND ".join(conditions)
    total = db.execute(
        "SELECT COUNT(*) AS total FROM products p LEFT JOIN categories c ON c.id = p.category_id" + where,
        params,
    ).fetchone()["total"]
    pager = paginate(total, page, current_app.config["ITEMS_PER_PAGE"])

    rows = db.execute(
        BASE_SELECT + where +
        f" ORDER BY {SORT_OPTIONS[sort_key][1]} LIMIT ? OFFSET ?",
        params + [pager["per_page"], pager["offset"]],
    ).fetchall()

    categories = _categories()
    active_category_name = ""
    if category_slug:
        match = next((c for c in categories if c["slug"] == category_slug), None)
        active_category_name = match["name"] if match else ""

    return render_template(
        "shop/products.html",
        products=rows,
        categories=categories,
        query=query,
        category=category_slug,
        active_category_name=active_category_name,
        sort_key=sort_key,
        sort_options=SORT_OPTIONS,
        min_rating=min_rating,
        pager=pager,
        wishlist=wishlist_ids(g.user["id"] if g.user else None),
        active_category="shop",
    )


@bp.route("/categories")
def categories():
    db = get_db()
    rows = _categories()
    showcase = {}
    for row in rows:
        showcase[row["slug"]] = db.execute(
            BASE_SELECT + " WHERE p.category_id = ? AND p.is_active = 1 "
                          "ORDER BY p.rating DESC LIMIT 3",
            (row["id"],),
        ).fetchall()
    return render_template("shop/categories.html", categories=rows, showcase=showcase,
                           active_category="categories",
                           wishlist=wishlist_ids(g.user["id"] if g.user else None))


@bp.route("/product/<slug>")
def product_detail(slug):
    db = get_db()
    product = db.execute(BASE_SELECT + " WHERE p.slug = ?", (slug,)).fetchone()
    if product is None or not product["is_active"]:
        flash("That product is no longer available.", "error")
        return redirect(url_for("shop.products"))

    related = db.execute(
        BASE_SELECT + " WHERE p.category_id = ? AND p.id != ? AND p.is_active = 1 "
                      "ORDER BY p.rating DESC LIMIT 4",
        (product["category_id"], product["id"]),
    ).fetchall()

    rating_breakdown = []
    base = int(round(product["rating"]))
    for star in range(5, 0, -1):
        weight = max(0, 20 - abs(base - star) * 12)
        rating_breakdown.append({"star": star, "percent": weight})

    return render_template(
        "shop/detail.html",
        product=product,
        related=related,
        rating_breakdown=rating_breakdown,
        wishlist=wishlist_ids(g.user["id"] if g.user else None),
        active_category="shop",
    )


@bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    return redirect(url_for("shop.products", q=query))
