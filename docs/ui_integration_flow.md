# Hướng Dẫn Tích Hợp Giao Diện (HTML/JS) Cho Board & Thành Viên
*(Tài liệu giải thích luồng hoạt động UI/UX bằng ngôn ngữ đơn giản, dễ hiểu)*

---

## 1. Bức tranh tổng quan: Giao diện sẽ có thêm những nút gì?

Để người dùng có thể sử dụng các API Backend chúng ta vừa viết, trên giao diện trình duyệt sẽ xuất hiện thêm các thành phần sau:

```
[ Thanh Điều Hướng (Navbar) ]
┌────────────────────────────────────────────────────────────────────────┐
│ [Logo] Team Task Board  | [ 📂 Chọn Board ▼ ] [+ Tạo Board Mới]        │ (Góc phải: Avatar User)
└────────────────────────────────────────────────────────────────────────┘

[ Thanh Tiêu Đề Board (Board Header) ]
┌────────────────────────────────────────────────────────────────────────┐
│ Dự Án Website  [Chủ phòng]   |   [👥 Quản lý thành viên] [⚙️ Cài đặt Board]│
└────────────────────────────────────────────────────────────────────────┘
```

1. **Nút "Chọn Board" (Dropdown):** Bấm vào sẽ xổ ra danh sách các Board của tôi để chuyển qua lại nhanh.
2. **Nút "+ Tạo Board Mới":** Bấm vào mở hộp thoại (Modal) nhập tên và bấm Tạo.
3. **Nút "⚙️ Cài đặt Board":** (Chỉ Chủ phòng thấy) Đổi tên bảng hoặc bấm Xóa bảng.
4. **Nút "👥 Quản lý thành viên":** Bấm vào mở hộp thoại xem ai đang ở trong bảng, mời thêm bạn bè, đổi chức vụ hoặc đuổi người.

---

## 2. Luồng hoạt động (Flow) của từng tính năng trên Web

Mỗi tính năng sẽ tuân theo đúng 1 công thức 4 bước:
$$\text{Bấm nút trên màn hình} \longrightarrow \text{JS gửi đơn đi (Fetch API)} \longrightarrow \text{Nhận phản hồi từ Server} \longrightarrow \text{Cập nhật giao diện / Hiện thông báo}$$

---

### Flow 1: Xem và Chuyển Đổi Board (Board Switcher)

* **Người dùng thấy gì?** Một menu dropdown `[ Chọn Board ▼ ]` nằm trên thanh menu chính.
* **Quy trình hoạt động:**
  1. Khi trang web vừa tải xong, JavaScript tự động gọi:
     ```javascript
     GET /api/boards
     ```
  2. Server trả về danh sách các Board mà người dùng tham gia:
     `[{ id: 1, name: "Website", role: "owner" }, { id: 2, name: "Marketing", role: "member" }]`
  3. JavaScript vẽ các dòng này vào menu dropdown.
  4. Khi người dùng click vào board "Marketing", trình duyệt chuyển trang sang `/boards/2`.

---

### Flow 2: Tạo Board Mới

* **Người dùng thấy gì?** Bấm nút `[+ Tạo Board]` $\rightarrow$ Một cửa sổ nhỏ (Modal) hiện lên gồm ô "Tên bảng" và "Mô tả".
* **Quy trình hoạt động:**
  1. Người dùng điền tên bảng: *"Thiết kế Mobile App"*, bấm nút **Lưu**.
  2. JavaScript lấy dữ liệu và gửi lên:
     ```javascript
     POST /api/boards
     Body: { "name": "Thiết kế Mobile App", "description": "Làm bản demo Figma" }
     ```
  3. **Nếu thành công (`201 Created`):**
     * Server trả về thông tin bảng vừa tạo (kèm `id` mới, ví dụ `id: 5`).
     * JavaScript hiện thông báo xanh (Toast): *"Tạo bảng thành công!"*.
     * Tự động chuyển hướng trình duyệt vào ngay bảng mới: `window.location.href = '/boards/5'`.
  4. **Nếu có lỗi (`400 Bad Request`):**
     * Ví dụ quên nhập tên $\rightarrow$ hiện chữ đỏ dưới ô nhập: *"Tên bảng không được để trống"*.

---

### Flow 3: Đổi Tên hoặc Xóa Board (Cài đặt Board)

* **Điều kiện:** Nút `[⚙️ Cài đặt]` chỉ hiện lên khi người dùng có vai trò là **Chủ phòng (`owner`)**.
* **Quy trình Đổi tên:**
  1. Bấm `[⚙️ Cài đặt]` $\rightarrow$ Modal hiện ra với tên và mô tả hiện tại.
  2. Sửa tên thành *"Website V2"*, bấm **Lưu thay đổi**.
  3. JavaScript gửi yêu cầu:
     ```javascript
     PATCH /api/boards/<id>
     Body: { "name": "Website V2" }
     ```
  4. Khi Server báo thành công $\rightarrow$ Tiêu đề bảng trên màn hình tự đổi thành "Website V2" ngay lập tức mà không cần tải lại trang.
* **Quy trình Xóa bảng:**
  1. Trong Modal có nút đỏ nguy hiểm: **"Xóa Board này"**.
  2. Người dùng bấm xóa $\rightarrow$ Hiện cảnh báo xác nhận: *"Bạn có chắc chắn muốn xóa không? Tất cả công việc trong bảng sẽ mất hết!"*.
  3. Nếu bấm Đồng ý, JavaScript gửi:
     ```javascript
     DELETE /api/boards/<id>
     ```
  4. Thành công $\rightarrow$ Trình duyệt đưa người dùng về trang chủ `/`.

---

### Flow 4: Quản Lý Thành Viên (Thêm, Đổi vai trò, Đuổi người)

* **Người dùng thấy gì?** Bấm vào avatar nhóm hoặc nút `[👥 Thành viên]` $\rightarrow$ Cửa sổ Quản lý thành viên hiện ra.
* **Bên trong cửa sổ có 2 phần:**
  1. **Danh sách người hiện tại:** Hiển thị Tên, Email, Chức vụ (`Chủ phòng`, `Thành viên`, `Khách xem`).
  2. **Ô mời bạn mới:** Ô nhập tên tài khoản hoặc mã số + Chọn chức vụ + Nút Mời.

#### Chi tiết các thao tác:
* **Mời thành viên mới:**
  * Chủ phòng nhập tên tài khoản (ví dụ: `ben`), chọn chức vụ `member`, bấm **Mời**.
  * JS gửi: `POST /api/boards/<id>/members` với `{ "identity": "ben", "role": "member" }`.
  * Thành công $\rightarrow$ Dòng của `ben` xuất hiện ngay vào danh sách bên dưới.
  * Nếu `ben` đã ở trong bảng rồi $\rightarrow$ Server báo lỗi 400 $\rightarrow$ JS hiện cảnh báo: *"Người này đã ở trong bảng rồi!"*.

* **Đổi chức vụ của ai đó:**
  * Cạnh tên mỗi người có 1 ô chọn (Dropdown): `[Thành viên ▼]`.
  * Khi Chủ phòng đổi sang `[Khách xem]`:
  * JS gửi ngay: `PATCH /api/boards/<id>/members/<user_id>` với `{ "role": "viewer" }`.
  * Nếu Chủ phòng duy nhất cố tình hạ chức chính mình $\rightarrow$ Server chặn báo lỗi $\rightarrow$ JS hiện: *"Bạn là chủ phòng duy nhất, không thể tự hạ chức mình!"*.

* **Đuổi người hoặc Tự rời bảng:**
  * Cạnh mỗi người có nút thùng rác 🗑️ (hoặc nút **"Rời bảng"** nếu là chính mình).
  * Bấm nút $\rightarrow$ JS hỏi xác nhận $\rightarrow$ Gửi: `DELETE /api/boards/<id>/members/<user_id>`.
  * Thành công $\rightarrow$ Xóa dòng của người đó khỏi danh sách, các công việc mà người đó từng nhận làm sẽ tự động đổi thành "Chưa giao cho ai" (Unassigned).

---

## 3. Bản đồ các file cần can thiệp khi làm giao diện

Khi bắt tay vào code giao diện, chúng ta sẽ đụng vào 3 file:

| Tên file | Nhiệm vụ cụ thể |
|---|---|
| **1. `app/templates/kanban/base.html`** | Thêm menu dropdown Chọn Board và nút "+ Tạo Board" trên thanh Navbar trên cùng. |
| **2. `app/templates/kanban/board.html`** | Thêm nút `[Cài đặt Board]`, nút `[Quản lý thành viên]` và các khung HTML Modal tương ứng. |
| **3. `app/static/kanban/js/kanban.js`** | Viết các hàm JavaScript bắt sự kiện click nút, gọi `fetch()` đến API và vẽ dữ liệu lên màn hình. |

---

## 4. Đoạn code JavaScript mẫu minh họa (Rất dễ hiểu)

Ví dụ hàm gọi API tạo bảng mới trong JavaScript:

```javascript
// Khi người dùng bấm nút "Lưu Board Mới"
async function handleCreateBoard(name, description) {
  try {
    // 1. Gửi dữ liệu lên API mà chúng ta vừa làm ở Backend
    const response = await fetch('/api/boards', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
      },
      body: JSON.stringify({ name: name, description: description })
    });

    const data = await response.json();

    if (!response.ok) {
      // 2. Nếu Backend báo lỗi (ví dụ chưa điền tên)
      alert("Lỗi: " + (data.detail || "Không thể tạo bảng"));
      return;
    }

    // 3. Nếu thành công, nhảy ngay vào bảng mới
    window.location.href = `/boards/${data.id}`;

  } catch (error) {
    alert("Lỗi kết nối mạng, vui lòng thử lại!");
  }
}
```

---

## 5. Tóm lại: Người dùng sẽ trải nghiệm thế nào?
Mọi thao tác Tạo bảng, Đổi tên, Xóa bảng, Mời bạn, Đổi quyền diễn ra **mượt mà ngay trên màn hình**, không bị giật lag hay trắng trang (nhờ dùng Fetch API / AJAX gọi ngầm xuống Server). Mọi luật bảo mật (không xóa bậy, không bỏ trống chủ phòng) đều đã được Backend bảo vệ 100%.
