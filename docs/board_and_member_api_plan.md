# Kế Hoạch Làm Tính Năng Quản Lý Bảng (Board) & Thành Viên
*(Bản giải thích đơn giản, dễ hiểu cho người mới bắt đầu)*

---

## 1. Tính năng này làm cái gì? (Giải thích đời thường)

Bạn hãy tưởng tượng hệ thống giống như ứng dụng **Trello** hoặc nhóm làm việc:
1. **Bạn muốn tạo một "Bảng công việc" mới** (ví dụ: "Dự án cuối kỳ", "Việc nhà").
2. **Bạn muốn xem danh sách các Bảng** mà mình đang tham gia.
3. **Bạn muốn đổi tên hoặc xóa Bảng** khi xong việc.
4. **Bạn muốn mời bạn bè vào Bảng**, phân chức vụ:
   - **Chủ phòng (`owner`)**: Toàn quyền sinh sát (sửa, xóa bảng, đuổi người).
   - **Thành viên (`member`)**: Được thêm việc, làm việc, bình luận.
   - **Khách xem (`viewer`)**: Chỉ được vào xem và bình luận, không được sửa xóa.
5. **Đổi vai trò hoặc kick người ra khỏi Bảng**.

---

## 2. Cách hệ thống hoạt động: Hãy tưởng tượng như "Vào một tòa nhà"

Mỗi khi người dùng bấm một nút trên màn hình (ví dụ nút "Tạo bảng"), dữ liệu sẽ đi qua các trạm sau:

```
[Màn hình bấm nút]
       │
       ▼
1. Trạm Soát Vé (board_forms.py)   --> Kiểm tra vé có hợp lệ không? (Tên bảng có bị để trống không?)
       │
       ▼
2. Trạm Bảo Vệ (guards.py)         --> Kiểm tra thẻ: Bạn có quyền làm việc này không? (Có phải Chủ phòng không?)
       │
       ▼
3. Quầy Xử Lý (boards.py)          --> Nhận lệnh, lưu thông tin vào Sổ cái (Database)
       │
       ▼
4. Bộ Phận Đóng Gói (serializers.py)--> Đóng gói kết quả sạch sẽ, đẹp đẽ gửi lại cho màn hình hiển thị
       │
       ▼
[Màn hình hiển thị kết quả thành công!]
```

---

## 3. Danh sách các file cần làm và nhiệm vụ của từng file

Chúng ta sẽ có **3 file tạo mới** và **4 file cũ cần sửa thêm một chút**.

---

### PHẦN A: CÁC FILE TẠO MỚI (Làm mới hoàn toàn)

#### 1. File `app/api/board_forms.py` — "Người soát vé"
* **Nhiệm vụ:** Kiểm tra dữ liệu người dùng gửi lên xem có đúng định dạng không trước khi cho vào trong.
* **Cụ thể nó kiểm tra gì?**
  * *Khi tạo bảng:* Tên bảng có bị rỗng không? Tên có bị dài quá 100 chữ không?
  * *Khi mời thành viên:* Người được mời có tồn tại mã số không? Vai trò giao cho họ (`owner`, `member`, `viewer`) có đúng 3 chữ này không hay người dùng gõ linh tinh?
* **Nếu sai:** Chặn lại ngay ở cửa và báo lỗi: *"Tên bảng không được để trống!"*.
* **Nếu đúng:** Cho đi tiếp vào trạm sau.

---

#### 2. File `app/api/boards.py` — "Người điều phối / Quầy xử lý chính"
* **Nhiệm vụ:** Là nơi tiếp nhận trực tiếp yêu cầu từ người dùng và ra lệnh cho Cơ sở dữ liệu (Database).
* **Cụ thể nó phục vụ những món nào?**
  1. **Xem danh sách Bảng (`GET /api/boards`):** Tìm xem người này đang ở trong những bảng nào rồi trả về danh sách.
  2. **Tạo Bảng mới (`POST /api/boards`):** Tạo một bảng mới, đồng thời tự động phong cho người tạo làm **Chủ phòng (`owner`)**.
  3. **Đổi tên/Mô tả Bảng (`PATCH /api/boards/<id>`):** Nhờ bảo vệ kiểm tra xem có phải Chủ phòng không, nếu đúng thì cho đổi tên bảng.
  4. **Xóa Bảng (`DELETE /api/boards/<id>`):** Chỉ Chủ phòng mới được xóa. Xóa bảng xong thì các công việc bên trong cũng tự mất theo.
  5. **Mời người vào Bảng (`POST /api/boards/<id>/members`):** Chủ phòng điền mã số bạn bè và chức vụ để thêm họ vào bảng.
  6. **Đổi chức vụ (`PATCH /api/boards/<id>/members/<user_id>`):** Nâng hoặc hạ chức vụ của ai đó (ví dụ từ Khách lên Thành viên).
  7. **Đuổi người / Rời nhóm (`DELETE /api/boards/<id>/members/<user_id>`):** Chủ phòng có quyền đuổi người; hoặc một người tự xin rút khỏi nhóm.

---

#### 3. File `tests/test_board_api.py` — "Thanh tra chất lượng tự động"
* **Nhiệm vụ:** Một con bot tự động bấm thử tất cả các chức năng để chắc chắn code chạy đúng, không bị lỗi ngớ ngẩn.
* **Nó sẽ thử những trò gì?**
  * Thử tạo bảng xem có thành công không.
  * Thử lấy tài khoản người xem bình thường đi xóa bảng xem hệ thống có biết chặn lại và báo *"Bạn không có quyền"* không.
  * Thử mời một người 2 lần vào cùng 1 bảng xem hệ thống có biết báo lỗi không.
  * Thử hạ chức của Chủ phòng duy nhất xem hệ thống có ngăn lại không.

---

### PHẦN B: CÁC FILE CÓ SẴN CẦN SỬA THÊM

#### 4. File `app/api/guards.py` — "Bảo vệ kiểm tra quyền"
* **Cần thêm gì?** Thêm các câu hỏi kiểm tra:
  * *"Người này có phải Chủ phòng không?"* (Nếu phải thì mới cho sửa/xóa bảng, thêm/bớt người).
  * *"Người này có quyền đuổi người này không?"* (Chỉ Chủ phòng mới được đuổi người khác, người bình thường chỉ được phép tự rút lui khỏi bảng của chính mình).

#### 5. File `app/api/serializers.py` — "Đóng gói quà tặng"
* **Cần thêm gì?** Sau khi lấy dữ liệu từ Database, dữ liệu rất lộn xộn. File này sẽ xếp gọn lại thành từng gói quà JSON đẹp mắt:
  * Gói thông tin Bảng: Mã số bảng, Tên bảng, Mô tả, Vai trò của tôi trong bảng, Bảng có bao nhiêu người, có bao nhiêu việc...
  * Gói thông tin Thành viên: Mã thành viên, Tên đăng nhập, Email, Vai trò...

#### 6. File `app/api/__init__.py` — "Bật công tắc kích hoạt"
* **Cần thêm gì?** Thêm đúng 1 dòng để báo cho hệ thống Flask biết là: *"Tôi vừa tạo thêm file `boards.py` đấy nhé, hãy nạp nó vào hệ thống để các đường dẫn bắt đầu hoạt động"*.

#### 7. File `app/api/tasks.py` — "Dọn dẹp cho gọn"
* **Cần làm gì?** Trước đây có một hàm xem chi tiết bảng đang nằm tạm ở file này. Ta chỉ cần kiểm tra xem nó có bị trùng với file `boards.py` mới tạo không, nếu trùng thì dọn cho gọn gàng.

---

## 4. Ba "Luật Bất Thành Văn" bắt buộc hệ thống phải bảo đảm

1. **Bảng không bao giờ được phép "vô chủ":**
   * Một bảng bắt buộc phải có ít nhất 1 Chủ phòng (`owner`).
   * Nếu bảng chỉ có duy nhất 1 Chủ phòng, người đó **không được phép tự hạ chức mình** hoặc **tự rời nhóm** (phải chuyển quyền cho người khác trước rồi mới được đi).
2. **Không mời trùng người:**
   * Một người đã ở trong bảng rồi thì không được phép mời thêm lần nữa.
3. **Người ngoài không được hóng chuyện:**
   * Nếu người dùng không tham gia vào Bảng, họ thậm chí không được phép biết bảng đó có tồn tại hay không (báo lỗi `404 Không tìm thấy`).

---

## 5. Thứ tự làm từng bước (Làm cái nào trước, cái nào sau?)

* **Bước 1:** Dạy bảo vệ luật trước $\rightarrow$ Sửa [`guards.py`](file:///c:/Users/hilln/OneDrive/Documents/PWD/Team-Task-Board/app/api/guards.py) và chuẩn bị hộp đóng gói [`serializers.py`](file:///c:/Users/hilln/OneDrive/Documents/PWD/Team-Task-Board/app/api/serializers.py).
* **Bước 2:** Đặt người soát vé ở cửa $\rightarrow$ Tạo [`board_forms.py`](file:///c:/Users/hilln/OneDrive/Documents/PWD/Team-Task-Board/app/api/board_forms.py).
* **Bước 3:** Mở quầy phục vụ $\rightarrow$ Tạo [`boards.py`](file:///c:/Users/hilln/OneDrive/Documents/PWD/Team-Task-Board/app/api/boards.py) và bật công tắc ở [`__init__.py`](file:///c:/Users/hilln/OneDrive/Documents/PWD/Team-Task-Board/app/api/__init__.py).
* **Bước 4:** Cho thanh tra vào chấm điểm $\rightarrow$ Tạo [`tests/test_board_api.py`](file:///c:/Users/hilln/OneDrive/Documents/PWD/Team-Task-Board/tests/) và chạy lệnh kiểm tra tự động xem xanh hết chưa.
