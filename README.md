# Discord Pokemon Game (Python)

Game bot Discord dùng dữ liệu từ `pokemon-data.json-master` để tạo trải nghiệm Pokémon cơ bản.

## Tính năng đã có

- `/start`
  - Giới thiệu game theo 2 trang.
  - Trang 2 chọn **gen starter (1-9)**.
  - Trang 3 chọn **1 trong 3 starter của gen đã chọn** (tổng 27 starter).
  - Nhận thưởng đầu game: **25 Poké Ball** + **1000 PokéDollars**.
- `/walk`
  - Mỗi lần gặp **5 Pokémon hoang dã**.
  - Chọn 1 Pokémon để vào battle.
- Battle cơ bản theo cơ chế gốc (đã sửa các vấn đề bạn nêu)
  - Tính **Speed** để quyết định ai đi trước mỗi lượt.
  - Nếu Pokémon của bạn gục sẽ tự động đổi Pokémon còn sống.
  - Nếu bắt được Pokémon khi party đủ 6 thì tự động gửi vào **PC**.
- Bắt Pokémon bằng item trong battle
  - Nút `Ném Ball` để chọn loại ball đang có trong túi (Poké Ball/Great Ball/Ultra Ball/... nếu có) và bắt Pokémon hoang dã.
- `/inventory` và `/inv`
  - Hiển thị túi đồ theo 5 ngăn:
    - Items (Hold items, General items, Battle items)
    - Pokeballs
    - Berries
    - TMs (Machines)
    - Key Items
- `/center` và `/c`
  - Hồi đầy HP cho toàn bộ Pokémon trong party (mô phỏng Pokémon Center).
- `/pinfo`
  - Xem chi tiết Pokémon trong party theo slot: stats (đã tính base+IV+EV+nature), IV, EV, nature, EXP hiện có, EXP cần để lên cấp, type, ảnh thumbnail (đọc từ `pokemon-data.json-master/images/pokedex/thumbnails`), hold item và moves.
- `/pc`
  - `action=view`: xem party + PC.
  - `action=send party_slot:<n>`: gửi Pokémon từ party vào PC.
  - `action=take pc_slot:<n>`: lấy Pokémon từ PC ra party.

## Cấu trúc chính

- `bot.py`: slash commands + Discord UI.
- `game/data_loader.py`: nạp pokedex/moves/items/types từ JSON.
- `game/logic.py`: model player/pokémon + battle engine.
- `game/storage.py`: lưu dữ liệu người chơi vào `data/players.json`.

## Cài đặt

1. Cài Python 3.10+.
2. Cài thư viện:

```bash
pip install -r requirements.txt
```

3. Tạo file `.env` từ `.env.example` và điền token:

```env
DISCORD_TOKEN=your_discord_bot_token_here
AUTO_SYNC_COMMANDS=true
GUILD_ID=your_test_server_id_optional
```

**Tối ưu tốc độ:**
- `AUTO_SYNC_COMMANDS=true`: auto sync slash commands khi khởi động (đặt `false` sau khi sync xong lần đầu để bot khởi động nhanh hơn).
- `GUILD_ID`: nếu điền ID server test, bot sync slash command chỉ vào server đó (nhanh hơn sync global nhiều lần).

4. Chạy bot:

```bash
python bot.py
```

## Lưu ý

- Bot đọc dữ liệu trực tiếp từ thư mục ngang cấp: `../pokemon-data.json-master`.
- Nếu bạn đổi vị trí thư mục, cần giữ đúng cấu trúc hoặc sửa path trong `game/data_loader.py`.

## Deploy Render (Background Worker)

Project đã có sẵn file [render.yaml](render.yaml) để deploy bot trên Render.

### 1) Chuẩn bị repo

- Đảm bảo thư mục dữ liệu `pokemon-data.json-master` có trong repo deploy.
- Có thể đặt dữ liệu ở 1 trong 2 vị trí:
  - `PFFPKM/pokemon-data.json-master` (khuyên dùng trên Render)
  - hoặc thư mục cha như local hiện tại.

### 2) Tạo service trên Render

- Vào Render → New + → Blueprint.
- Chọn repo chứa project này, Render sẽ đọc `render.yaml` và tạo Worker.

### 3) Cấu hình biến môi trường

- Bắt buộc: `DISCORD_TOKEN`.
- Tuỳ chọn nếu data đặt custom path: `POKEMON_DATA_ROOT`.

### Lưu dữ liệu trên Render Free (không có Disk)

Nếu không dùng Persistent Disk, dữ liệu file local có thể mất sau deploy/restart.
Để lưu vĩnh viễn, dùng MongoDB Atlas (free tier):

- Set các env trên Render:
  - `MONGODB_URI`
  - `MONGODB_DB` (ví dụ `pffpkm`)
  - `MONGODB_COLLECTION` (ví dụ `players`)

Khi `MONGODB_URI` được set, bot sẽ tự động lưu player vào MongoDB thay vì `data/players.json`.

### 4) Deploy

- Bấm Deploy, chờ build xong.
- Kiểm tra logs có dòng `Logged in as ...` là bot đã online.

### 5) Khuyến nghị production

- Đặt `AUTO_SYNC_COMMANDS=false` để bot khởi động nhanh và ổn định hơn.

## Giả lập kiểm tra cơ chế battle

Chạy script sau để kiểm tra nhanh các cơ chế: STAB, Physical/Special theo chỉ số, Speed order, flow lượt + faint skip, burn effect, type matchup.

```bash
python tools/battle_mechanics_sim.py
```
