const DATA_URL = './assets/data/products.json';
const IMG_PLACEHOLDER = 'https://images.unsplash.com/photo-1607301405390-0e2f9c322e99?q=80&w=1600&auto=format&fit=crop';

async function fetchProducts() {
  const res = await fetch(DATA_URL);
  if (!res.ok) throw new Error('상품 데이터를 불러오지 못했습니다');
  return res.json();
}

function formatPrice(value) {
  return new Intl.NumberFormat('ko-KR').format(value);
}

function getCart() {
  try { return JSON.parse(localStorage.getItem('cart') || '[]'); } catch { return []; }
}
function setCart(cart) {
  localStorage.setItem('cart', JSON.stringify(cart));
}
function updateCartCount() {
  const count = getCart().reduce((sum, i) => sum + i.qty, 0);
  const el = document.getElementById('cart-count');
  if (el) el.textContent = String(count);
}

function addToCart(product, qty = 1) {
  const cart = getCart();
  const idx = cart.findIndex((i) => i.id === product.id);
  if (idx >= 0) cart[idx].qty += qty; else cart.push({ id: product.id, name: product.name, price: product.price, image: product.image, qty });
  setCart(cart);
  updateCartCount();
}

// Home
async function loadNewArrivals() {
  const list = await fetchProducts();
  const grid = document.getElementById('new-arrivals-grid');
  if (!grid) return;
  const items = list.slice(0, 8).map(renderProductCard).join('');
  grid.innerHTML = items;
}

// Products list
function bindProductFilters({ onChange }) {
  const inputs = ['search', 'category', 'sort'].map((id) => document.getElementById(id));
  inputs.forEach((el) => el && el.addEventListener('input', onChange));
}

async function renderProductsList() {
  const [list, searchEl, categoryEl, sortEl] = await Promise.all([
    fetchProducts(),
    Promise.resolve(document.getElementById('search')),
    Promise.resolve(document.getElementById('category')),
    Promise.resolve(document.getElementById('sort')),
  ]);

  const search = (searchEl?.value || '').trim();
  const category = categoryEl?.value || '';
  const sort = sortEl?.value || 'recent';

  let filtered = list
    .filter((p) => !category || p.category === category)
    .filter((p) => !search || p.name.includes(search));

  if (sort === 'price-asc') filtered = filtered.sort((a, b) => a.price - b.price);
  if (sort === 'price-desc') filtered = filtered.sort((a, b) => b.price - a.price);

  const grid = document.getElementById('products-grid');
  if (!grid) return;
  grid.innerHTML = filtered.map(renderProductCard).join('');
}

function renderProductCard(p) {
  const img = p.image || IMG_PLACEHOLDER;
  const price = formatPrice(p.price);
  const url = `/frontend/product.html?id=${encodeURIComponent(p.id)}`;
  return `
  <article class="card">
    <a href="${url}"><img src="${img}" alt="${p.name}" loading="lazy" /></a>
    <div class="card-body">
      <div class="card-title">${p.name}</div>
      <div class="muted">${p.category}</div>
      <div class="card-price">${price}원</div>
      <a class="btn" href="${url}">자세히 보기</a>
    </div>
  </article>`;
}

// Product detail
async function loadProductDetail() {
  const params = new URLSearchParams(location.search);
  const id = params.get('id');
  if (!id) return;
  const list = await fetchProducts();
  const product = list.find((p) => String(p.id) === String(id));
  if (!product) return;

  const img = product.image || IMG_PLACEHOLDER;
  document.getElementById('product-image').src = img;
  document.getElementById('product-name').textContent = product.name;
  document.getElementById('product-desc').textContent = product.description || '';
  document.getElementById('product-price').textContent = formatPrice(product.price);

  const qtyEl = document.getElementById('qty');
  document.getElementById('inc').addEventListener('click', () => qtyEl.value = String(Number(qtyEl.value || '1') + 1));
  document.getElementById('dec').addEventListener('click', () => qtyEl.value = String(Math.max(1, Number(qtyEl.value || '1') - 1)));
  document.getElementById('add-to-cart').addEventListener('click', () => addToCart(product, Number(qtyEl.value || '1')));
}

// Cart page
async function renderCartPage() {
  const list = await fetchProducts();
  const cart = getCart();
  const idToProduct = new Map(list.map((p) => [p.id, p]));
  const itemsEl = document.getElementById('cart-items');
  const summaryEl = document.getElementById('cart-summary');
  if (!itemsEl || !summaryEl) return;

  if (cart.length === 0) {
    itemsEl.innerHTML = '<p class="muted">장바구니가 비었습니다.</p>';
    summaryEl.innerHTML = '';
    return;
  }

  let subtotal = 0;
  itemsEl.innerHTML = cart.map((i) => {
    const p = idToProduct.get(i.id);
    const img = (p?.image) || IMG_PLACEHOLDER;
    const price = p?.price ?? i.price;
    const line = price * i.qty;
    subtotal += line;
    return `
      <div class="cart-item">
        <img src="${img}" alt="${i.name}" />
        <div>
          <div class="cart-item-title">${i.name}</div>
          <div class="muted">${formatPrice(price)}원 × ${i.qty}</div>
          <div>
            <button data-action="dec" data-id="${i.id}">−</button>
            <button data-action="inc" data-id="${i.id}">＋</button>
            <button data-action="remove" data-id="${i.id}">삭제</button>
          </div>
        </div>
        <div>${formatPrice(line)}원</div>
      </div>`;
  }).join('');

  const shipping = subtotal >= 50000 ? 0 : 3000;
  const total = subtotal + shipping;
  summaryEl.innerHTML = `
    <div>상품금액: <strong>${formatPrice(subtotal)}원</strong></div>
    <div>배송비: <strong>${formatPrice(shipping)}원</strong></div>
    <div>결제금액: <strong>${formatPrice(total)}원</strong></div>`;

  itemsEl.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const id = btn.getAttribute('data-id');
    const action = btn.getAttribute('data-action');
    const cart = getCart();
    const idx = cart.findIndex((x) => String(x.id) === String(id));
    if (idx < 0) return;
    if (action === 'inc') cart[idx].qty += 1;
    if (action === 'dec') cart[idx].qty = Math.max(1, cart[idx].qty - 1);
    if (action === 'remove') cart.splice(idx, 1);
    setCart(cart);
    renderCartPage();
    updateCartCount();
  }, { once: true });
}

// Checkout
async function renderCheckoutSummary() {
  const list = await fetchProducts();
  const cart = getCart();
  const idToProduct = new Map(list.map((p) => [p.id, p]));
  const wrap = document.getElementById('checkout-summary');
  if (!wrap) return;

  if (cart.length === 0) {
    wrap.innerHTML = '<p class="muted">장바구니가 비었습니다.</p>';
    return;
  }

  let subtotal = 0;
  const items = cart.map((i) => {
    const p = idToProduct.get(i.id);
    const price = p?.price ?? i.price;
    const line = price * i.qty;
    subtotal += line;
    return `<div>${i.name} × ${i.qty} = ${formatPrice(line)}원</div>`;
  }).join('');
  const shipping = subtotal >= 50000 ? 0 : 3000;
  const total = subtotal + shipping;
  wrap.innerHTML = `${items}
  <hr />
  <div>상품금액: <strong>${formatPrice(subtotal)}원</strong></div>
  <div>배송비: <strong>${formatPrice(shipping)}원</strong></div>
  <div>결제금액: <strong>${formatPrice(total)}원</strong></div>`;
}

function completeCheckout() {
  const name = document.getElementById('name').value.trim();
  const phone = document.getElementById('phone').value.trim();
  const address = document.getElementById('address').value.trim();
  if (!name || !phone || !address) {
    alert('필수 정보를 입력하세요.');
    return;
  }
  localStorage.removeItem('cart');
  updateCartCount();
  alert('주문이 완료되었습니다. 감사합니다!');
  location.href = '/frontend/index.html';
}

