"""ByteBodega catalogue and demo accounts, loaded on first run only."""

from datetime import datetime

from werkzeug.security import generate_password_hash

CATEGORIES = [
    ("Laptops & Tablets", "laptops-tablets",
     "Notebooks and tablets for coursework, notes and coding.", "laptop"),
    ("Monitors & Displays", "monitors-displays",
     "Second screens and portable displays for a dual-monitor setup.", "monitor"),
    ("Keyboards & Mice", "keyboards-mice",
     "Mechanical boards, compact keyboards and ergonomic mice.", "keyboard"),
    ("Audio & Headsets", "audio-headsets",
     "Headsets, earbuds and speakers for calls, labs and focus.", "headphones"),
    ("Storage & Drives", "storage-drives",
     "SSDs, memory cards and flash drives for projects and backups.", "drive"),
    ("Hubs, Cables & Power", "hubs-cables-power",
     "Docks, adapters, chargers and cables that connect everything.", "plug"),
    ("Dev Boards & Kits", "dev-boards-kits",
     "Microcontrollers, sensors and kits for hardware projects.", "cpu"),
]

# name, slug, category slug, price, stock, rating, rating_count, badge, image keyword, description
PRODUCTS = [
    ("Lenovo IdeaPad Slim 3 15 (Ryzen 5)", "lenovo-ideapad-slim-3", "laptops-tablets",
     32995.00, 12, 4.6, 148, "Best seller", "laptop computer desk",
     "Ryzen 5 7000-series processor with 16 GB RAM and a 512 GB SSD. The 15.6-inch "
     "anti-glare screen and 1.62 kg frame make it an easy daily carry for lectures and labs."),
    ("ASUS Vivobook 15 (Core i5)", "asus-vivobook-15", "laptops-tablets",
     36995.00, 9, 4.5, 112, "", "laptop notebook computer",
     "12th-gen Intel Core i5, 16 GB memory and 512 GB storage in a fingerprint-reader "
     "chassis. Enough headroom for Android Studio, virtual machines and a dozen browser tabs."),
    ("Apple MacBook Air 13\" M2", "macbook-air-13-m2", "laptops-tablets",
     54990.00, 6, 4.9, 203, "Pro pick", "macbook air laptop",
     "Silent, fanless M2 performance with 8 GB unified memory and a 256 GB SSD. Up to "
     "18 hours of battery keeps a full day of classes and coding sessions covered."),
    ("Acer Aspire Go 15 (Core i3)", "acer-aspire-go-15", "laptops-tablets",
     24995.00, 14, 4.3, 96, "Value pick", "laptop student desk",
     "A no-frills 15.6-inch notebook with an i3-N305, 8 GB RAM and 256 GB SSD. Fine for "
     "documents, research, Python exercises and streaming between classes."),
    ("Samsung Galaxy Tab S6 Lite (2024)", "samsung-galaxy-tab-s6-lite", "laptops-tablets",
     18990.00, 10, 4.5, 176, "", "tablet samsung device",
     "10.4-inch display with the S Pen included, so you can annotate PDFs and write "
     "lecture notes by hand. 64 GB storage with a microSD slot for extra room."),

    ("Dell P2422H 24\" IPS Monitor", "dell-p2422h-24-monitor", "monitors-displays",
     8995.00, 15, 4.7, 134, "", "computer monitor office",
     "Full HD IPS panel with 99% sRGB coverage and ComfortView Plus low blue light. "
     "Height, tilt, swivel and pivot adjustment, plus HDMI, DisplayPort and VGA inputs."),
    ("ASUS TUF VG249Q1A 24\" 165Hz", "asus-tuf-vg249q1a", "monitors-displays",
     10495.00, 11, 4.8, 158, "Best seller", "gaming monitor setup",
     "165 Hz IPS panel with 1 ms MPRT and FreeSync Premium for tear-free play. Two HDMI "
     "ports and DisplayPort let a laptop and console share the same screen."),
    ("LG 27MP400 27\" IPS Monitor", "lg-27mp400-monitor", "monitors-displays",
     8295.00, 13, 4.4, 87, "", "monitor display desk",
     "27 inches of Full HD IPS with a 75 Hz refresh rate and AMD FreeSync. Slim bezels "
     "and a simple stand make it an easy second screen for code and documentation."),
    ("Xiaomi A27i 27\" IPS Monitor", "xiaomi-a27i-monitor", "monitors-displays",
     7495.00, 16, 4.3, 64, "Value pick", "computer screen desk",
     "Full HD 100 Hz panel with 8-bit colour and wide viewing angles. HDMI and "
     "DisplayPort inputs cover a laptop, desktop and console without a switcher."),
    ("Arzopa 15.6\" Portable Monitor", "arzopa-15-6-portable-monitor", "monitors-displays",
     6995.00, 18, 4.2, 59, "New", "portable monitor laptop",
     "A 1080p IPS screen that runs from a single USB-C cable and weighs under 800 g. "
     "The magnetic folio cover doubles as a stand for group projects and hackathons."),

    ("Keychron K2 V2 Mechanical Keyboard", "keychron-k2-v2", "keyboards-mice",
     4990.00, 20, 4.7, 186, "Best seller", "mechanical keyboard",
     "75% wireless board with hot-swappable Gateron brown switches and a 4000 mAh "
     "battery. Mac and Windows layouts are both printed and switchable."),
    ("Royal Kludge RK61 60% Keyboard", "royal-kludge-rk61", "keyboards-mice",
     2290.00, 28, 4.4, 231, "Value pick", "mechanical keyboard rgb",
     "Triple-mode 60% board (Bluetooth, 2.4 GHz and USB-C) with hot-swap sockets and "
     "RGB. Compact enough to leave desk space for a notebook during lectures."),
    ("Logitech MX Keys S", "logitech-mx-keys-s", "keyboards-mice",
     6490.00, 12, 4.8, 121, "Pro pick", "wireless keyboard desk",
     "Low-profile backlit keys with smart illumination and three-device switching. "
     "USB-C charging lasts up to ten days with the backlight on."),
    ("Logitech MX Master 3S", "logitech-mx-master-3s", "keyboards-mice",
     5290.00, 17, 4.8, 209, "", "wireless mouse",
     "8,000 DPI tracking on any surface, quiet clicks and the MagSpeed wheel that "
     "scrolls 1,000 lines a second. Pairs with three machines at once."),
    ("Razer DeathAdder V2 X HyperSpeed", "razer-deathadder-v2-x", "keyboards-mice",
     2590.00, 22, 4.5, 143, "", "gaming mouse",
     "Wireless ergonomic shape with a 14K DPI sensor and up to 235 hours on one AA "
     "battery. Programmable side buttons map neatly to IDE shortcuts."),

    ("Sony WH-CH720N Headphones", "sony-wh-ch720n", "audio-headsets",
     5990.00, 16, 4.6, 172, "", "headphones black",
     "Lightweight noise cancelling over-ears at 192 g with up to 35 hours of battery. "
     "Multipoint pairing keeps a laptop and phone connected at the same time."),
    ("HyperX Cloud III Gaming Headset", "hyperx-cloud-iii", "audio-headsets",
     4490.00, 14, 4.7, 138, "Best seller", "gaming headset",
     "Angled 53 mm drivers with DTS Spatial Audio and a detachable noise-cancelling "
     "mic. Works over USB or 3.5 mm with a laptop, console or phone."),
    ("Apple AirPods Pro 2 (USB-C)", "airpods-pro-2-usbc", "audio-headsets",
     14990.00, 8, 4.8, 264, "", "wireless earbuds",
     "Active noise cancellation, adaptive audio and a USB-C charging case. Six hours "
     "per charge and thirty with the case for commutes and library sessions."),
    ("JBL Go 4 Portable Speaker", "jbl-go-4", "audio-headsets",
     2499.00, 30, 4.5, 197, "Value pick", "bluetooth speaker",
     "Pocket-sized JBL Pro Sound with IP67 dust and water resistance. Seven hours of "
     "playtime and Auracast pairing for dorm rooms and weekend trips."),
    ("Moondrop CHU II IEM Earphones", "moondrop-chu-ii", "audio-headsets",
     1290.00, 35, 4.4, 88, "New", "earphones in ear",
     "10 mm dynamic drivers in a machined metal shell with a detachable cable. A cheap, "
     "detailed pair for focused listening during long coding stretches."),

    ("Samsung T7 1TB Portable SSD", "samsung-t7-1tb-ssd", "storage-drives",
     5490.00, 20, 4.8, 212, "Best seller", "external ssd drive",
     "Up to 1,050 MB/s over USB 3.2 Gen 2 in a 58 g aluminium body. AES 256-bit "
     "encryption keeps thesis files and project repositories safe."),
    ("WD Elements 2TB Portable HDD", "wd-elements-2tb", "storage-drives",
     4290.00, 15, 4.5, 164, "", "hard drive external",
     "Two terabytes of plug-and-play storage over USB 3.0. A simple way to archive "
     "videos, virtual machines and years of school files."),
    ("SanDisk Ultra 128GB microSDXC", "sandisk-ultra-128gb-microsd", "storage-drives",
     890.00, 50, 4.6, 302, "Value pick", "memory card",
     "A1-rated card with up to 140 MB/s read speed and an SD adapter included. Fits "
     "tablets, action cameras, drones and the Raspberry Pi in your kit."),
    ("Kingston DataTraveler Exodia 128GB", "kingston-dt-exodia-128gb", "storage-drives",
     590.00, 60, 4.3, 258, "", "usb flash drive",
     "USB 3.2 Gen 1 flash drive with a protective cap and key loop. Handy for bootable "
     "installers, lab submissions and printing errands."),
    ("Crucial BX500 480GB SATA SSD", "crucial-bx500-480gb", "storage-drives",
     2190.00, 18, 4.6, 141, "", "ssd internal drive",
     "A 2.5-inch SATA drive rated at 540 MB/s read and 500 MB/s write. The cheapest way "
     "to make an ageing student laptop feel new again."),

    ("UGREEN 6-in-1 USB-C Hub", "ugreen-6-in-1-usb-c-hub", "hubs-cables-power",
     1890.00, 26, 4.6, 193, "Best seller", "usb hub",
     "Adds 4K HDMI, two USB-A ports, 100 W USB-C pass-through charging and SD/microSD "
     "readers from a single port. Essential for laptops that dropped their ports."),
    ("Anker 737 24,000mAh Power Bank", "anker-737-power-bank", "hubs-cables-power",
     6490.00, 12, 4.7, 126, "", "power bank",
     "140 W of USB-C output charges a laptop, tablet and phone together. The smart "
     "display reports remaining capacity and real-time wattage."),
    ("Baseus GaN5 Pro 65W Charger", "baseus-gan5-pro-65w", "hubs-cables-power",
     1790.00, 24, 4.5, 149, "Value pick", "usb c charger",
     "Three ports and 65 W of gallium nitride power in a foldable plug. Replaces a "
     "laptop brick and a phone charger in one bag slot."),
    ("UGREEN 100W USB-C Cable 2m", "ugreen-100w-usb-c-cable", "hubs-cables-power",
     499.00, 45, 4.4, 217, "", "usb c cable",
     "Braided 100 W PD cable rated for 480 Mbps data and 10,000 bends. Two metres is "
     "long enough to reach the outlet behind a dorm desk."),
    ("TP-Link UE300 USB Gigabit Adapter", "tp-link-ue300-adapter", "hubs-cables-power",
     790.00, 32, 4.5, 102, "", "ethernet cable network",
     "USB 3.0 to Gigabit Ethernet adapter for wired connections in labs and dormitories. "
     "No drivers needed on Windows, macOS or Linux."),

    ("Raspberry Pi 5 8GB Board", "raspberry-pi-5-8gb", "dev-boards-kits",
     5490.00, 15, 4.8, 96, "Pro pick", "raspberry pi board",
     "Quad-core 2.4 GHz Arm CPU, PCIe and dual 4K display output in a credit-card "
     "board. Runs Linux servers, Python projects and coursework VMs; needs a 27 W USB-C supply."),
    ("Arduino Uno R3 Starter Kit", "arduino-uno-r3-starter-kit", "dev-boards-kits",
     1690.00, 25, 4.6, 178, "Best seller", "arduino electronics",
     "Uno-compatible board with a breadboard, 65 jumper wires, LEDs, sensors, a servo "
     "and a guided lesson booklet. The usual starting point for embedded systems class."),
    ("ESP32 DevKit V1 3-Pack", "esp32-devkit-v1-3-pack", "dev-boards-kits",
     890.00, 40, 4.5, 133, "Value pick", "esp32 microcontroller",
     "Dual-core ESP32 boards with Wi-Fi and Bluetooth for IoT prototypes. Three boards "
     "in one pack cover the lab, the capstone and a spare."),
    ("Raspberry Pi Pico W 2-Pack", "raspberry-pi-pico-w-2-pack", "dev-boards-kits",
     1190.00, 30, 4.6, 74, "New", "raspberry pi pico",
     "RP2040 microcontroller with wireless networking and pre-soldered headers. "
     "Programmable in MicroPython or C for sensors, displays and small robots."),
]

DEMO_USERS = [
    ("Mika Santos", "admin", "admin@bytebodega.ph", "Admin@123", "admin",
     "0917 555 0101", "12 Ayala Avenue", "Makati City", "Metro Manila", "1226"),
    ("Juan Dela Cruz", "juan", "juan@example.com", "Juan@1234", "customer",
     "0917 555 0142", "88 Katipunan Avenue, Brgy. Loyola Heights", "Quezon City", "Metro Manila", "1108"),
]


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def seed_if_empty(connection):
    """Insert demo data the first time the database is created."""
    if connection.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"] > 0:
        return

    now = _now()
    category_ids = {}
    for name, slug, description, icon in CATEGORIES:
        cursor = connection.execute(
            "INSERT INTO categories (name, slug, description, icon, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, slug, description, icon, now),
        )
        category_ids[slug] = cursor.lastrowid

    for name, slug, category_slug, price, stock, rating, rating_count, badge, _keyword, description in PRODUCTS:
        connection.execute(
            """INSERT INTO products
                   (name, slug, category_id, price, description, stock, rating, rating_count, image, badge, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, slug, category_ids[category_slug], price, description, stock, rating,
             rating_count, f"img/products/{slug}.jpg", badge, now),
        )

    for full_name, username, email, password, role, phone, address, city, province, postal in DEMO_USERS:
        connection.execute(
            """INSERT INTO users
                   (full_name, username, email, password_hash, role, phone, address, city, province,
                    postal_code, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (full_name, username, email, generate_password_hash(password), role, phone, address,
             city, province, postal, now),
        )

    connection.commit()
