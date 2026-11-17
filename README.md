# ByteBodega

**ByteBodega** is a gadget shop for IT students, built as a complete online
shopping system with **Python (Flask)** and **SQLite**. It ships a customer
storefront, a full shopping cart and checkout, order management, a customer
profile area, and a separate administrator console.

Everything is server-rendered with Jinja templates, a hand-written CSS design
system and a small amount of vanilla JavaScript — no build step, no Node.js.

---

## 1. Demo accounts

| Role     | Username | Email               | Password    |
|----------|----------|---------------------|-------------|
| Customer | `juan`   | juan@example.com    | `Juan@1234` |
| Admin    | `admin`  | admin@bytebodega.ph | `Admin@123` |

Both accounts log in from the same page. Administrators are redirected to
`/admin`; customers land on the storefront. New customers can register freely.

---

## 2. What is included

**Storefront**
- Home page with hero, category strip, top-rated grid and new arrivals
- 34 IT-student gadgets across 7 categories (Laptops & Tablets, Monitors &
  Displays, Keyboards & Mice, Audio & Headsets, Storage & Drives, Hubs, Cables
  & Power, Dev Boards & Kits)
- Product cards with photo, name, description, peso price, star rating, stock,
  Add to Cart, Add to Wishlist and Details buttons
- Search, category filter, rating filter, sorting and pagination
- Product detail page with quantity stepper, stock info, rating breakdown and
  related products

**Cart and checkout**
- Add, remove, increase/decrease, type a quantity, clear the cart
- Live subtotal, shipping fee (₱79, free over ₱2,500) and total
- Item count badges in the sidebar and header
- Checkout with customer information, delivery address, contact number, order
  summary, payment method (Cash on Delivery / GCash demo) and Place Order
- Order confirmation page with a saved payment reference

**Customer account**
- Login (username *or* email, remember me, show/hide password)
- Registration with validation (unique username/email, password rules)
- Forgot password → 6-digit reset code (shown on screen; no mail server)
- Order history with status tabs, order detail with progress timeline and
  cancellation for pending/processing orders
- Wishlist with move-to-cart
- Profile editing, delivery address and password change
- Notification centre (order updates, account messages, mark as read)

**Admin console**
- Dashboard: total products, customers, orders, sales, 7-day chart, pipeline,
  recent orders and low-stock alerts
- Product management: create, edit, hide/show, delete, photo upload or URL
- Category management: create, rename, delete (blocked while products exist)
- Customer management: search, deactivate/reactivate accounts
- Order management: filter, search, view, and progress statuses
  (Pending → Processing → Shipped → Delivered, or cancel with restock)
- Sales reports: gross sales, average order value, monthly chart, revenue by
  category, best sellers and status breakdown

**Technical**
- SQLite database with 9 tables, foreign keys and indexes
- Passwords hashed with PBKDF2-SHA256 (`werkzeug.security`)
- Session-based authentication with customer/admin separation
- Server-side validation and flash messages for every action
- Data persists across restarts in `instance/bytebodega.db`
- Responsive layout for desktop, tablet and mobile

---

## 3. Run it

### Option A — double-click `start.bat` (Windows)
It creates the virtual environment, installs the two dependencies and starts
the server. Then open <http://127.0.0.1:5000>.

### Option B — terminal
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The database and sample data are created automatically on first start.

Already on this machine? The virtual environment exists, so you can go straight to
`.venv\Scripts\python.exe run.py`.

> **Port note:** another app on this computer is already listening on port 5000,
> so `run.py` automatically tries 5077 next and prints the address it used.
> The preview for this session is running on <http://127.0.0.1:5077>.

---

## 4. Move the project into Visual Studio Code

1. **Install VS Code** — <https://code.visualstudio.com> (Python is already
   installed on this machine at `C:\Users\jaype\AppData\Local\Programs\Python\Python312`).
2. **Install the Python extension** — open the Extensions panel (`Ctrl+Shift+X`),
   search “Python” (Microsoft) and install it.
3. **Open the folder** — `File → Open Folder…` and choose
   `C:\Users\jaype\OneDrive\Documents\Navarro1st`. All project files are already
   in this folder; nothing needs to be copied or exported.
4. **Select the interpreter** — `Ctrl+Shift+P` → *Python: Select Interpreter* →
   pick `.venv\Scripts\python.exe` inside the project folder.
5. **Open a terminal** (`Ctrl+``) and check the environment:
   ```bat
   .venv\Scripts\python.exe -c "import flask; print(flask.__version__)"
   ```
   If that fails, run `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
6. **Run the app** — press `F5` (a “Run ByteBodega (Flask)” launch
   configuration is included) or run `python run.py` in the terminal.
7. **Open** <http://127.0.0.1:5000> in your browser and log in with one of the
   demo accounts above.

`.vscode/launch.json` and `.vscode/settings.json` are already configured, so
breakpoints, the debugger and the virtual environment work immediately.

> If the debugger reports that port 5000 is taken, change `"args"`-free launch to
> run through `run.py` (it is) or set the environment variable `PORT=5077` in the
> `env` block of `.vscode/launch.json`.

> The `App.java` and `public class Main {.java` files in this folder are
> unrelated leftovers from an earlier exercise and are not used by this project.

---

## 5. Project structure

```
Navarro1st/
├─ run.py                 # start the development server
├─ config.py              # paths, shipping rules, secret key
├─ requirements.txt
├─ start.bat              # one-click Windows launcher
├─ instance/              # SQLite database + secret key (created at runtime)
├─ app/
│  ├─ __init__.py         # app factory, filters, context, error pages
│  ├─ db.py               # connection handling and schema bootstrap
│  ├─ schema.sql          # 9-table relational schema
│  ├─ seed.py             # 34 products, 7 categories, 2 demo accounts
│  ├─ services.py         # auth guards, cart maths, notifications, pagination
│  ├─ auth.py             # login, register, forgot/reset password, logout
│  ├─ shop.py             # home, catalogue, search, product detail
│  ├─ cart.py             # cart + wishlist actions
│  ├─ checkout.py         # checkout, payment, order confirmation
│  ├─ orders.py           # order history, detail, cancellation
│  ├─ profile.py          # profile editing and password change
│  ├─ notifications.py    # notification centre
│  └─ admin.py            # admin dashboard, CRUD, orders, reports
├─ templates/             # Jinja templates (customer, auth, admin, errors)
├─ static/
│  ├─ css/style.css       # design system + responsive rules
│  ├─ js/app.js           # sidebar, password toggle, toasts, steppers
│  └─ img/products/       # 34 product photographs
└─ tools/
   ├─ fetch_images.py     # re-download product photos (optional)
   └─ smoke_test.py       # 87 automated end-to-end checks
```

---

## 6. Testing

```bat
.venv\Scripts\python.exe tools\smoke_test.py
```

The suite runs against a throwaway database (`instance/test_bytebodega.db`) so your
real data is never modified. It exercises registration, login, search and
filters, cart quantity controls, wishlist, checkout totals, stock updates, order
cancellation, profile and password changes, password reset, notifications, and
every admin CRUD and order-status action — 87 checks in total.

---

## 7. Notes

- **Photos** are sample product photography from
  [Pexels](https://www.pexels.com) (free to use, no attribution required),
  downloaded once into `static/img/products/`. Re-run
  `.venv\Scripts\python.exe tools\fetch_images.py --force` to refresh them.
- **GCash** is a demonstration payment method: the order records a paid
  transaction reference, but no real money moves.
- **Password reset** shows the 6-digit code on screen because there is no mail
  server configured. Wire it to an email provider before real-world use.
- This is an academic demonstration build. For production, add CSRF protection,
  HTTPS, a WSGI server (gunicorn/waitress) and a managed database.
