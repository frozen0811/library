document.addEventListener('DOMContentLoaded', () => {
    const seatMap = document.getElementById('seat-map');
    const floorSelector = document.querySelector('.floor-selector');
    const floorStatsDiv = document.getElementById('floor-stats');
    const actionPanel = document.getElementById('action-panel');

    let currentFloor = 1;
    let selectedSeatId = null;
    let reservationTimer = null;

    const loadSeats = async (floor) => {

        if (reservationTimer) clearInterval(reservationTimer);
        const response = await fetch(`/api/seats/${floor}`);
        const data = await response.json();

        renderSeats(data.seats, data.my_seat_id);
        updateFloorStats(data.seats);
    };


    const renderSeats = (seats, mySeatId) => {
        seatMap.innerHTML = '';
        actionPanel.innerHTML = '';
        selectedSeatId = null;

        const userHasReservation = mySeatId !== null;
        seats.forEach(seat => {
            const seatDiv = document.createElement('div');
            seatDiv.id = `seat-${seat.id}`;
            seatDiv.dataset.id = seat.id;
            seatDiv.innerHTML = `<span>${seat.seat_number.split('-')[1]}</span>`;
            
            let seatClass = seat.status;
            let isInteractive = false;

            if (userHasReservation) {
                if (seat.id === mySeatId) {
                    isInteractive = true;
                    seatClass += ' my-reservation';
                } else {
                    seatClass = 'unavailable';
                }
            } else {
                if (seat.status === 'available') {
                    isInteractive = true;
                }
            }

            seatDiv.className = `seat ${seatClass}`;
            if (isInteractive) seatDiv.classList.add('interactive');
            if (seat.status === 'reserved' && seat.id === mySeatId) {
                const timeDiv = document.createElement('div');
                timeDiv.className = 'time-remaining';
                timeDiv.dataset.time = seat.reservation_time;
                seatDiv.appendChild(timeDiv);
            }
            seatMap.appendChild(seatDiv);
        });
        startReservationTimer();
        updateActionPanel(mySeatId);
    };

    const updateFloorStats = (seats) => {
        const availableCount = seats.filter(s => s.status === 'available').length;
        floorStatsDiv.textContent = `本层共 ${seats.length} 个座位，当前空闲 ${availableCount} 个。`;
    };

    const updateActionPanel = (mySeatId) => {
        if (mySeatId) {
            actionPanel.innerHTML = `<button id="release-btn" class="btn-danger" data-id="${mySeatId}">释放座位</button>`;
            document.getElementById('release-btn').addEventListener('click', handleReleaseSeat);
        } else if (selectedSeatId) {
            actionPanel.innerHTML = `<button id="confirm-btn" class="btn-primary" data-id="${selectedSeatId}">确认预约</button>`;
            document.getElementById('confirm-btn').addEventListener('click', handleConfirmReservation);
        }
    };

    floorSelector.addEventListener('click', (e) => {
        if (e.target.classList.contains('floor-btn')) {
            const floor = e.target.dataset.floor;

            if (floor !== currentFloor) {
                currentFloor = floor;
                loadSeats(currentFloor);
                document.querySelector('.floor-btn.active').classList.remove('active');
                e.target.classList.add('active');
            }
        }
    });

    seatMap.addEventListener('click', (e) => {
        const seatDiv = e.target.closest('.seat.interactive');
        if (!seatDiv) return;
        const seatId = seatDiv.dataset.id;

        if (seatDiv.classList.contains('available')) {
            const currentSelected = document.querySelector('.seat.selected');
            if (currentSelected) {
                currentSelected.classList.remove('selected');
                currentSelected.classList.add('available');
            }

            if (selectedSeatId === seatId) {
                selectedSeatId = null;
            } else {
                seatDiv.classList.remove('available');
                seatDiv.classList.add('selected');
                selectedSeatId = seatId;
            }
            updateActionPanel(null);
        }
    });

    const handleConfirmReservation = async (e) => {
        const seatId = e.target.dataset.id;
        const response = await fetch(`/api/reserve/${seatId}`, { method: 'POST' });
        const data = await response.json();
        alert(data.message);

        if (data.success) {
            loadSeats(currentFloor);
        }
    };

    const handleReleaseSeat = async (e) => {
        const seatId = e.target.dataset.id;
        if (confirm('确定要释放您的座位吗？')) {
            const response = await fetch(`/api/release/${seatId}`, { method: 'POST' });
            const data = await response.json();
            alert(data.message);
            if (data.success) {
                loadSeats(currentFloor);
            }
        }
    };

    
    const startReservationTimer = () => {
        const timeElements = document.querySelectorAll('.time-remaining');
        if (timeElements.length === 0) return;

        reservationTimer = setInterval(() => {
            timeElements.forEach(el => {
                const reservationTime = new Date(el.dataset.time + 'Z');
                const expiryTime = new Date(reservationTime.getTime() + 60 * 60 * 1000);
                const diff = expiryTime - new Date();

                if (diff <= 0) {
                    el.textContent = '已超时';
                } else {
                    const minutes = Math.floor((diff / 1000 / 60) % 60);
                    const seconds = Math.floor((diff / 1000) % 60);
                    el.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                }
            });
        }, 1000);
    };

    
    loadSeats(currentFloor);
});