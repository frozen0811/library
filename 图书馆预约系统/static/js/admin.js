document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.admin-content h1')?.textContent === '预约管理') {
        initReservationManagement();
    }
    if (document.querySelector('.admin-content h1')?.textContent === '账号管理') {
        initAccountManagement();
    }

    function initReservationManagement() {
        const seatMap = document.getElementById('seat-map');
        const floorSelector = document.querySelector('.floor-selector');
        let currentFloor = 1;

        const modalHTML = `
            <div id="admin-modal" class="modal-backdrop">
                <div class="modal-content">
                    <h3 id="modal-title" class="modal-title">修改座位状态</h3>
                    <div id="modal-actions" class="modal-actions">
                        <button data-status="available">设为 可预约</button>
                        <button data-status="reserved">设为 已被预约</button>
                        <button data-status="occupied">设为 已占用</button>
                        <button data-status="unavailable">设为 无法预约</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        const modal = document.getElementById('admin-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalActions = document.getElementById('modal-actions');

        let currentEditingSeatId = null;
        const loadSeats = async (floor) => {
            const response = await fetch(`/api/seats/${floor}`);
            const data = await response.json();
            renderSeats(data.seats);
        };

        const renderSeats = (seats) => {
            seatMap.innerHTML = '';
            seats.forEach(seat => {
                const seatDiv = document.createElement('div');
                seatDiv.className = `seat ${seat.status} interactive`;
                seatDiv.dataset.id = seat.id;
                seatDiv.dataset.number = seat.seat_number;
                seatDiv.innerHTML = `
                    <span>${seat.seat_number.split('-')[1]}</span>
                    <small style="font-size:10px; display:block;">${seat.username || 'N/A'}</small>
                `;
                seatMap.appendChild(seatDiv);
            });
        };

        floorSelector.addEventListener('click', (e) => {
            if (e.target.classList.contains('floor-btn')) {
                currentFloor = e.target.dataset.floor;
                loadSeats(currentFloor);
                document.querySelector('.floor-btn.active').classList.remove('active');
                e.target.classList.add('active');
            }
        });

        seatMap.addEventListener('click', (e) => {
            const seatDiv = e.target.closest('.seat');
            if (!seatDiv) return;

            currentEditingSeatId = seatDiv.dataset.id;
            const seatNumber = seatDiv.dataset.number;
            modalTitle.textContent = `修改座位 ${seatNumber} 的状态`;
            modal.style.display = 'flex';
        });

        modalActions.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON') {
                const newStatus = e.target.dataset.status;

                if (currentEditingSeatId && newStatus) {
                    fetch(`/api/admin/seat/status/${currentEditingSeatId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: newStatus })
                    })
                    .then(res => res.json())
                    .then(data => {
                        alert(data.message);
                        if (data.success) {
                            loadSeats(currentFloor);
                        }
                    })
                    .finally(() => {
                        modal.style.display = 'none';
                    });
                }
            }
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
        loadSeats(currentFloor);
    }

    function initAccountManagement() {
        const userTableBody = document.getElementById('user-table-body');
        const loadUsers = async () => {
            const response = await fetch('/api/admin/users');
            const users = await response.json();
            renderUsers(users);
        };
        const renderUsers = (users) => {
            userTableBody.innerHTML = '';
            users.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${user.id}</td>
                    <td>${user.username}</td>
                    <td><button class="btn-danger delete-btn" data-id="${user.id}">删除</button></td>
                `;
                userTableBody.appendChild(row);
            });
        };
        userTableBody.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-btn')) {
                const userId = e.target.dataset.id;
                if (confirm(`确定要删除ID为 ${userId} 的用户吗？该用户的所有预约将一并取消。`)) {
                    fetch(`/api/admin/users/delete/${userId}`, { method: 'DELETE' })
                    .then(res => res.json())
                    .then(data => {
                        alert(data.message);
                        if (data.success) {
                            loadUsers();
                        }
                    });
                }
            }
        });
        loadUsers();
    }
});