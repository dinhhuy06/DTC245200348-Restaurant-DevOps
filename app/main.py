import os
from decimal import Decimal, InvalidOperation

import psycopg
from psycopg.rows import dict_row
from flask import Flask, abort, redirect, render_template, request, url_for

app = Flask(__name__)


def get_db():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        row_factory=dict_row,
        connect_timeout=5,
    )


def read_name():
    name = request.form.get("name", "").strip()
    if not name or len(name) > 100:
        abort(400, "Tên phải có từ 1 đến 100 ký tự.")
    return name


def read_price():
    try:
        price = Decimal(request.form.get("price", ""))
        if not price.is_finite() or price < 0 or price > 999999999:
            raise ValueError()
        return price.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        abort(400, "Giá tiền không hợp lệ.")


@app.get("/")
def index():
    with get_db() as db:
        dishes = db.execute(
            "SELECT * FROM dishes ORDER BY id"
        ).fetchall()

        tables = db.execute("""
            SELECT t.*,
                   EXISTS(
                       SELECT 1 FROM orders o
                       WHERE o.table_id = t.id AND o.status = 'open'
                   ) AS occupied
            FROM restaurant_tables t
            ORDER BY t.id
        """).fetchall()

        orders = db.execute("""
            SELECT o.id, o.table_id, o.status, o.created_at,
                   t.name AS table_name,
                   COALESCE(SUM(i.quantity * i.unit_price), 0) AS total
            FROM orders o
            JOIN restaurant_tables t ON t.id = o.table_id
            LEFT JOIN order_items i ON i.order_id = o.id
            GROUP BY o.id, t.name
            ORDER BY o.id DESC
        """).fetchall()

        items = db.execute("""
            SELECT i.*, d.name AS dish_name
            FROM order_items i
            JOIN dishes d ON d.id = i.dish_id
            ORDER BY i.id
        """).fetchall()

    return render_template(
        "index.html",
        dishes=dishes,
        tables=tables,
        orders=orders,
        items=items,
    )


@app.post("/dishes")
def add_dish():
    name = read_name()
    price = read_price()
    with get_db() as db:
        db.execute(
            "INSERT INTO dishes (name, price) VALUES (%s, %s)",
            (name, price),
        )
    return redirect(url_for("index"))


@app.post("/dishes/<int:dish_id>/edit")
def edit_dish(dish_id):
    name = read_name()
    price = read_price()
    with get_db() as db:
        result = db.execute(
            "UPDATE dishes SET name = %s, price = %s WHERE id = %s",
            (name, price, dish_id),
        )
        if result.rowcount == 0:
            abort(404, "Không tìm thấy món ăn.")
    return redirect(url_for("index"))


@app.post("/dishes/<int:dish_id>/delete")
def delete_dish(dish_id):
    with get_db() as db:
        used = db.execute(
            "SELECT 1 FROM order_items WHERE dish_id = %s LIMIT 1",
            (dish_id,),
        ).fetchone()
        if used:
            abort(409, "Món đã có trong đơn hàng, không thể xóa.")

        db.execute("DELETE FROM dishes WHERE id = %s", (dish_id,))
    return redirect(url_for("index"))


@app.post("/tables")
def add_table():
    name = read_name()
    with get_db() as db:
        db.execute(
            "INSERT INTO restaurant_tables (name) VALUES (%s)",
            (name,),
        )
    return redirect(url_for("index"))


@app.post("/tables/<int:table_id>/edit")
def edit_table(table_id):
    name = read_name()
    with get_db() as db:
        result = db.execute(
            "UPDATE restaurant_tables SET name = %s WHERE id = %s",
            (name, table_id),
        )
        if result.rowcount == 0:
            abort(404, "Không tìm thấy bàn.")
    return redirect(url_for("index"))


@app.post("/tables/<int:table_id>/delete")
def delete_table(table_id):
    with get_db() as db:
        used = db.execute(
            "SELECT 1 FROM orders WHERE table_id = %s LIMIT 1",
            (table_id,),
        ).fetchone()
        if used:
            abort(409, "Bàn đã có lịch sử đơn hàng, không thể xóa.")

        db.execute(
            "DELETE FROM restaurant_tables WHERE id = %s",
            (table_id,),
        )
    return redirect(url_for("index"))


@app.post("/orders")
def create_order():
    table_id = request.form.get("table_id", type=int)
    if not table_id:
        abort(400, "Hãy chọn bàn.")

    with get_db() as db:
        table = db.execute(
            "SELECT id FROM restaurant_tables WHERE id = %s FOR UPDATE",
            (table_id,),
        ).fetchone()
        if not table:
            abort(404, "Không tìm thấy bàn.")

        existing = db.execute("""
            SELECT id FROM orders
            WHERE table_id = %s AND status = 'open'
        """, (table_id,)).fetchone()
        if existing:
            abort(409, "Bàn đang có đơn chưa thanh toán.")

        db.execute(
            "INSERT INTO orders (table_id) VALUES (%s)",
            (table_id,),
        )

    return redirect(url_for("index"))


@app.post("/orders/<int:order_id>/items")
def add_order_item(order_id):
    dish_id = request.form.get("dish_id", type=int)
    quantity = request.form.get("quantity", type=int)
    if not dish_id or quantity is None or not 1 <= quantity <= 100:
        abort(400, "Chọn món và số lượng từ 1 đến 100.")

    with get_db() as db:
        order = db.execute(
            "SELECT status FROM orders WHERE id = %s FOR UPDATE",
            (order_id,),
        ).fetchone()
        if not order:
            abort(404, "Không tìm thấy đơn hàng.")
        if order["status"] != "open":
            abort(409, "Đơn đã đóng, không thể thêm món.")

        dish = db.execute(
            "SELECT price FROM dishes WHERE id = %s",
            (dish_id,),
        ).fetchone()
        if not dish:
            abort(404, "Không tìm thấy món ăn.")

        db.execute("""
            INSERT INTO order_items
                (order_id, dish_id, quantity, unit_price)
            VALUES (%s, %s, %s, %s)
        """, (order_id, dish_id, quantity, dish["price"]))

    return redirect(url_for("index"))


@app.post("/items/<int:item_id>/quantity")
def update_quantity(item_id):
    quantity = request.form.get("quantity", type=int)
    if quantity is None or not 1 <= quantity <= 100:
        abort(400, "Số lượng phải từ 1 đến 100.")

    with get_db() as db:
        item = db.execute("""
            SELECT o.status
            FROM order_items i
            JOIN orders o ON o.id = i.order_id
            WHERE i.id = %s
            FOR UPDATE OF o
        """, (item_id,)).fetchone()
        if not item:
            abort(404, "Không tìm thấy dòng món.")
        if item["status"] != "open":
            abort(409, "Đơn đã đóng, không thể sửa.")

        db.execute(
            "UPDATE order_items SET quantity = %s WHERE id = %s",
            (quantity, item_id),
        )

    return redirect(url_for("index"))


@app.post("/items/<int:item_id>/delete")
def delete_item(item_id):
    with get_db() as db:
        item = db.execute("""
            SELECT o.status
            FROM order_items i
            JOIN orders o ON o.id = i.order_id
            WHERE i.id = %s
            FOR UPDATE OF o
        """, (item_id,)).fetchone()
        if not item:
            abort(404, "Không tìm thấy dòng món.")
        if item["status"] != "open":
            abort(409, "Đơn đã đóng, không thể xóa món.")

        db.execute(
            "DELETE FROM order_items WHERE id = %s",
            (item_id,),
        )

    return redirect(url_for("index"))


@app.post("/orders/<int:order_id>/close")
def close_order(order_id):
    with get_db() as db:
        result = db.execute("""
            UPDATE orders SET status = 'paid'
            WHERE id = %s AND status = 'open'
        """, (order_id,))
        if result.rowcount == 0:
            abort(409, "Đơn không tồn tại hoặc đã thanh toán.")

    return redirect(url_for("index"))


@app.get("/health")
def health():
    with get_db() as db:
        db.execute("SELECT 1")
    return {"status": "ok"}