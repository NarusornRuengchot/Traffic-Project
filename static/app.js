// =========================================================================
// KU SRC Smart Traffic WebSocket Client & Live Analytics Engine
// =========================================================================

class TrafficWebSocketApp {
    constructor() {
        this.ws = null;
        this.wsConnected = false;
        this.isRunning = false;
        this.isPaused = false;
        this.lastTelemetry = null;
        this.summaryEvents = [];
        
        // Chart instances
        this.timelineChart = null;
        this.classChart = null;
        this.timelineData = { labels: [], inbound: [], outbound: [], active: [] };
        
        // DOM Elements
        this.initDOMElements();
        this.initCharts();
        this.initEventListeners();
        this.loadAvailableModelsAndDevices();
        this.loadAvailableVideos();
        this.checkDatabaseStatus();
        this.connectWebSocket();
    }

    initDOMElements() {
        this.wsStatusEl = document.getElementById("wsStatus");
        this.statusDotEl = this.wsStatusEl.querySelector(".status-dot");
        this.statusTextEl = this.wsStatusEl.querySelector(".status-text");
        this.themeToggleBtn = document.getElementById("themeToggleBtn");

        // Database Elements
        this.dbStatusBadge = document.getElementById("dbStatusBadge");
        this.dbStatusText = document.getElementById("dbStatusText");
        this.historyModalBtn = document.getElementById("historyModalBtn");
        this.historyModal = document.getElementById("historyModal");
        this.closeHistoryBtn = document.getElementById("closeHistoryBtn");
        this.closeHistoryFooterBtn = document.getElementById("closeHistoryFooterBtn");
        this.refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
        this.historySearchInput = document.getElementById("historySearchInput");
        this.historyTableBody = document.getElementById("historyTableBody");
        this.dbInfoSubtitle = document.getElementById("dbInfoSubtitle");
        this.sessionDetailContainer = document.getElementById("sessionDetailContainer");
        this.closeDetailBtn = document.getElementById("closeDetailBtn");
        this.detailTitle = document.getElementById("detailTitle");
        this.detailMetaGrid = document.getElementById("detailMetaGrid");
        this.detailIntervalsBody = document.getElementById("detailIntervalsBody");

        // Controls
        this.videoSelect = document.getElementById("videoSelect");
        this.videoUploadInput = document.getElementById("videoUploadInput");
        this.uploadProgressText = document.getElementById("uploadProgressText");
        this.modelSelect = document.getElementById("modelSelect");
        this.confSlider = document.getElementById("confSlider");
        this.confVal = document.getElementById("confVal");
        this.classChecks = document.querySelectorAll(".class-check");
        this.imgSizeSelect = document.getElementById("imgSizeSelect");
        this.deviceSelect = document.getElementById("deviceSelect");
        this.frameSkipSlider = document.getElementById("frameSkipSlider");
        this.skipVal = document.getElementById("skipVal");
        this.lineYSlider = document.getElementById("lineYSlider");
        this.lineYVal = document.getElementById("lineYVal");
        this.midXSlider = document.getElementById("midXSlider");
        this.midXVal = document.getElementById("midXVal");
        this.swapDirToggle = document.getElementById("swapDirToggle");
        this.swapLabel = document.getElementById("swapLabel");
        this.filmingDate = document.getElementById("filmingDate");
        this.filmingTime = document.getElementById("filmingTime");

        // Buttons
        this.startBtn = document.getElementById("startBtn");
        this.pauseBtn = document.getElementById("pauseBtn");
        this.stopBtn = document.getElementById("stopBtn");
        this.downloadCsvBtn = document.getElementById("downloadCsvBtn");

        // Metrics
        this.inboundCardTitle = document.getElementById("inboundCardTitle");
        this.outboundCardTitle = document.getElementById("outboundCardTitle");
        this.inboundMetric = document.getElementById("inboundMetric");
        this.outboundMetric = document.getElementById("outboundMetric");
        this.inboundDensity = document.getElementById("inboundDensity");
        this.outboundDensity = document.getElementById("outboundDensity");
        this.trafficLevelMetric = document.getElementById("trafficLevelMetric");
        this.trafficLevelIcon = document.getElementById("trafficLevelIcon");
        this.realTimeClock = document.getElementById("realTimeClock");
        this.totalMetric = document.getElementById("totalMetric");
        this.stallRatioMetric = document.getElementById("stallRatioMetric");

        // Video Viewport
        this.videoStreamImg = document.getElementById("videoStreamImg");
        this.streamOverlay = document.getElementById("streamOverlay");
        this.fpsBadge = document.getElementById("fpsBadge");
        this.progressBadge = document.getElementById("progressBadge");
        this.progressBarFill = document.getElementById("progressBarFill");

        // Summary
        this.summarySection = document.getElementById("summarySection");
        this.summaryTableBody = document.getElementById("summaryTableBody");

        // Default filming date
        const today = new Date().toISOString().split("T")[0];
        this.filmingDate.value = today;
    }

    initCharts() {
        const ctxTimeline = document.getElementById("timelineChart").getContext("2d");
        this.timelineChart = new Chart(ctxTimeline, {
            type: "line",
            data: {
                labels: [],
                datasets: [
                    {
                        label: "Inbound",
                        borderColor: "#38bdf8",
                        backgroundColor: "rgba(56, 189, 248, 0.1)",
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.3,
                        data: []
                    },
                    {
                        label: "Outbound",
                        borderColor: "#f97316",
                        backgroundColor: "rgba(249, 115, 22, 0.1)",
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.3,
                        data: []
                    },
                    {
                        label: "Active Vehicles",
                        borderColor: "#22c55e",
                        backgroundColor: "rgba(34, 197, 94, 0.1)",
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.3,
                        data: []
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8", maxTicksLimit: 6 } },
                    y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" }, beginAtZero: true }
                },
                plugins: {
                    legend: { labels: { color: "#f1f5f9", boxWidth: 12 } }
                }
            }
        });

        const ctxClass = document.getElementById("classChart").getContext("2d");
        this.classChart = new Chart(ctxClass, {
            type: "bar",
            data: {
                labels: ["Car", "Motorcycle", "Bus", "Truck"],
                datasets: [{
                    label: "Count",
                    data: [0, 0, 0, 0],
                    backgroundColor: ["#38bdf8", "#818cf8", "#facc15", "#f87171"],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#94a3b8" } },
                    y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8", precision: 0 }, beginAtZero: true }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    initEventListeners() {
        this.themeToggleBtn.addEventListener("click", () => {
            document.body.classList.toggle("light-theme");
            const isLight = document.body.classList.contains("light-theme");
            this.themeToggleBtn.textContent = isLight ? "☀️" : "🌙";
        });

        this.confSlider.addEventListener("input", (e) => {
            this.confVal.textContent = parseFloat(e.target.value).toFixed(2);
            this.sendInFlightConfigUpdate();
        });

        this.frameSkipSlider.addEventListener("input", (e) => {
            this.skipVal.textContent = e.target.value;
            this.sendInFlightConfigUpdate();
        });

        this.lineYSlider.addEventListener("input", (e) => {
            this.lineYVal.textContent = Math.round(e.target.value * 100) + "%";
            this.sendInFlightConfigUpdate();
            if (!this.isRunning) this.updateCalibrationPreview();
        });

        this.midXSlider.addEventListener("input", (e) => {
            this.midXVal.textContent = Math.round(e.target.value * 100) + "%";
            this.sendInFlightConfigUpdate();
            if (!this.isRunning) this.updateCalibrationPreview();
        });

        this.swapDirToggle.addEventListener("change", (e) => {
            const swapped = e.target.checked;
            this.swapLabel.textContent = swapped ? "🔄 Left = Outbound | Right = Inbound" : "➡️ Left = Inbound | Right = Outbound";
            this.inboundCardTitle.textContent = swapped ? "Outbound Count (Left)" : "Inbound Count (Left)";
            this.outboundCardTitle.textContent = swapped ? "Inbound Count (Right)" : "Outbound Count (Right)";
            this.sendInFlightConfigUpdate();
            if (!this.isRunning) this.updateCalibrationPreview();
        });

        this.modelSelect.addEventListener("change", () => this.sendInFlightConfigUpdate());
        this.imgSizeSelect.addEventListener("change", () => this.sendInFlightConfigUpdate());
        this.deviceSelect.addEventListener("change", () => this.sendInFlightConfigUpdate());
        this.videoSelect.addEventListener("change", () => {
            if (!this.isRunning) this.updateCalibrationPreview();
        });

        this.classChecks.forEach(ch => {
            ch.addEventListener("change", () => this.sendInFlightConfigUpdate());
        });

        this.videoUploadInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) {
                this.uploadVideoFile(e.target.files[0]);
            }
        });

        this.startBtn.addEventListener("click", () => this.startAnalysis());
        this.pauseBtn.addEventListener("click", () => this.togglePause());
        this.stopBtn.addEventListener("click", () => this.stopAnalysis());
        this.downloadCsvBtn.addEventListener("click", () => this.downloadCSV());

        // Database & History Modal Listenners
        this.historyModalBtn.addEventListener("click", () => this.openHistoryModal());
        this.closeHistoryBtn.addEventListener("click", () => this.closeHistoryModal());
        this.closeHistoryFooterBtn.addEventListener("click", () => this.closeHistoryModal());
        this.refreshHistoryBtn.addEventListener("click", () => this.loadHistoryRecords());
        this.closeDetailBtn.addEventListener("click", () => {
            this.sessionDetailContainer.style.display = "none";
        });
        this.historySearchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            this.filterHistoryTable(query);
        });
        // Close modal on backdrop click
        this.historyModal.addEventListener("click", (e) => {
            if (e.target === this.historyModal) this.closeHistoryModal();
        });
    }

    async loadAvailableModelsAndDevices() {
        try {
            const res = await fetch("/api/models");
            const data = await res.json();
            
            this.modelSelect.innerHTML = "";
            data.models.forEach(m => {
                const opt = document.createElement("option");
                opt.value = m.name;
                opt.textContent = m.label;
                if (m.name === data.current_model) opt.selected = true;
                this.modelSelect.appendChild(opt);
            });

            this.deviceSelect.innerHTML = "";
            data.devices.forEach(d => {
                const opt = document.createElement("option");
                opt.value = d;
                opt.textContent = d === "cuda" ? "CUDA GPU (NVIDIA)" : "CPU";
                this.deviceSelect.appendChild(opt);
            });
        } catch (err) {
            console.error("Failed to load models/devices:", err);
        }
    }

    async loadAvailableVideos() {
        try {
            const res = await fetch("/api/videos");
            const data = await res.json();
            this.videoSelect.innerHTML = "";
            data.videos.forEach((v, idx) => {
                const opt = document.createElement("option");
                opt.value = v.path;
                opt.textContent = v.name;
                if (idx === 0) opt.selected = true;
                this.videoSelect.appendChild(opt);
            });
            if (data.videos.length > 0) {
                this.updateCalibrationPreview();
            }
        } catch (err) {
            console.error("Failed to load videos:", err);
        }
    }

    async updateCalibrationPreview() {
        const videoPath = this.videoSelect.value;
        if (!videoPath) return;

        const lineY = parseFloat(this.lineYSlider.value);
        const midX = parseFloat(this.midXSlider.value);
        const swap = this.swapDirToggle.checked;

        try {
            const res = await fetch(`/api/video-preview?path=${encodeURIComponent(videoPath)}&line_y=${lineY}&mid_x=${midX}&swap=${swap}`);
            if (res.ok) {
                const data = await res.json();
                if (data.preview && !this.isRunning) {
                    this.videoStreamImg.src = data.preview;
                }
            }
        } catch (err) {
            console.warn("Could not load preview:", err);
        }
    }

    async uploadVideoFile(file) {
        this.uploadProgressText.textContent = `Uploading ${file.name}...`;
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/upload", { method: "POST", body: formData });
            const data = await res.json();
            if (data.status === "success") {
                this.uploadProgressText.textContent = `✅ Uploaded: ${data.filename}`;
                await this.loadAvailableVideos();
                this.videoSelect.value = data.path;
                this.updateCalibrationPreview();
            }
        } catch (err) {
            this.uploadProgressText.textContent = `❌ Upload failed`;
            console.error("Upload error:", err);
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/traffic`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.wsConnected = true;
            this.wsStatusEl.className = "ws-status connected";
            this.statusTextEl.textContent = "WebSocket Connected (Active)";
        };

        this.ws.onclose = () => {
            this.wsConnected = false;
            this.wsStatusEl.className = "ws-status disconnected";
            this.statusTextEl.textContent = "WebSocket Disconnected. Reconnecting...";
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.ws.onerror = (err) => {
            console.error("WebSocket Error:", err);
        };

        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            this.handleWebSocketMessage(msg);
        };
    }

    handleWebSocketMessage(msg) {
        switch (msg.type) {
            case "started":
                this.isRunning = true;
                this.isPaused = false;
                this.updateButtonStates(true, false);
                this.streamOverlay.classList.add("hidden");
                this.summarySection.style.display = "none";
                this.resetCharts();
                break;

            case "frame":
                this.videoStreamImg.src = msg.frame;
                this.updateTelemetry(msg.telemetry);
                break;

            case "paused":
                this.isPaused = msg.is_paused;
                this.pauseBtn.textContent = this.isPaused ? "▶️ Resume" : "⏸️ Pause";
                break;

            case "stopped":
                this.isRunning = false;
                this.isPaused = false;
                this.updateButtonStates(false, false);
                this.streamOverlay.classList.remove("hidden");
                this.fpsBadge.textContent = "FPS: 0.0";
                this.updateCalibrationPreview();
                break;

            case "finished":
                this.isRunning = false;
                this.updateButtonStates(false, false);
                this.summaryEvents = msg.events_log || [];
                this.renderSummaryTable(msg.summary_table || []);
                this.summarySection.style.display = "block";
                this.fpsBadge.textContent = "FPS: 0.0";
                
                if (msg.session_id) {
                    console.log(`✅ Session #${msg.session_id} auto-saved to Database.`);
                }
                break;

            case "error":
                alert(`Error: ${msg.message}`);
                this.isRunning = false;
                this.updateButtonStates(false, false);
                break;
        }
    }

    updateTelemetry(telemetry) {
        if (!telemetry) return;
        this.lastTelemetry = telemetry;

        this.inboundMetric.textContent = telemetry.inbound_count;
        this.outboundMetric.textContent = telemetry.outbound_count;
        this.totalMetric.textContent = telemetry.total_count;

        this.inboundDensity.textContent = `Inbound Density: ${telemetry.inbound_active}`;
        this.outboundDensity.textContent = `Outbound Density: ${telemetry.outbound_active}`;

        this.trafficLevelIcon.textContent = telemetry.traffic_level_emoji || "🟢";
        this.trafficLevelMetric.textContent = telemetry.traffic_level_en || "Smooth";
        this.realTimeClock.textContent = `Clock: ${telemetry.real_time}`;

        const stallPct = Math.round((telemetry.stall_ratio || 0) * 100);
        this.stallRatioMetric.textContent = `Stall: ${stallPct}%`;

        if (telemetry.fps !== undefined) {
            this.fpsBadge.textContent = `FPS: ${telemetry.fps}`;
        }
        this.progressBadge.textContent = `${telemetry.progress_pct}%`;
        this.progressBarFill.style.width = `${telemetry.progress_pct}%`;

        this.appendTimelineData(telemetry.real_time, telemetry.inbound_count, telemetry.outbound_count, telemetry.active_vehicles);
        this.updateClassChart(telemetry.class_counts);
    }

    appendTimelineData(timeLabel, inbound, outbound, active) {
        if (this.timelineData.labels.length > 40) {
            this.timelineData.labels.shift();
            this.timelineData.inbound.shift();
            this.timelineData.outbound.shift();
            this.timelineData.active.shift();
        }

        this.timelineData.labels.push(timeLabel);
        this.timelineData.inbound.push(inbound);
        this.timelineData.outbound.push(outbound);
        this.timelineData.active.push(active);

        this.timelineChart.data.labels = this.timelineData.labels;
        this.timelineChart.data.datasets[0].data = this.timelineData.inbound;
        this.timelineChart.data.datasets[1].data = this.timelineData.outbound;
        this.timelineChart.data.datasets[2].data = this.timelineData.active;
        this.timelineChart.update();
    }

    updateClassChart(classCounts) {
        if (!classCounts) return;
        const counts = [
            classCounts["Car"] || 0,
            classCounts["Motorcycle"] || 0,
            classCounts["Bus"] || 0,
            classCounts["Truck"] || 0
        ];
        this.classChart.data.datasets[0].data = counts;
        this.classChart.update();
    }

    resetCharts() {
        this.timelineData = { labels: [], inbound: [], outbound: [], active: [] };
        this.timelineChart.data.labels = [];
        this.timelineChart.data.datasets.forEach(ds => ds.data = []);
        this.timelineChart.update();
    }

    getSelectedClasses() {
        const selected = [];
        this.classChecks.forEach(ch => {
            if (ch.checked) selected.push(ch.value);
        });
        return selected;
    }

    startAnalysis() {
        if (!this.wsConnected) {
            alert("WebSocket is not connected. Please wait a moment.");
            return;
        }

        if (this.isRunning) return;

        const dateStr = this.filmingDate.value || new Date().toISOString().split("T")[0];
        const timeStr = this.filmingTime.value || "08:30";
        const startDatetimeStr = `${dateStr} ${timeStr}:00`;

        const config = {
            video_path: this.videoSelect.value,
            model_name: this.modelSelect.value,
            conf_threshold: parseFloat(this.confSlider.value),
            img_size: parseInt(this.imgSizeSelect.value),
            device: this.deviceSelect.value,
            target_classes: this.getSelectedClasses(),
            frame_skip: parseInt(this.frameSkipSlider.value),
            line_y_ratio: parseFloat(this.lineYSlider.value),
            mid_x_ratio: parseFloat(this.midXSlider.value),
            swap_directions: this.swapDirToggle.checked,
            start_datetime_str: startDatetimeStr
        };

        this.ws.send(JSON.stringify({ action: "start", config: config }));
    }

    togglePause() {
        if (!this.isRunning || !this.wsConnected) return;
        this.ws.send(JSON.stringify({ action: "pause" }));
    }

    stopAnalysis() {
        if (!this.isRunning || !this.wsConnected) return;
        this.ws.send(JSON.stringify({ action: "stop" }));
    }

    sendInFlightConfigUpdate() {
        if (!this.wsConnected) return;
        const config = {
            model_name: this.modelSelect.value,
            conf_threshold: parseFloat(this.confSlider.value),
            img_size: parseInt(this.imgSizeSelect.value),
            device: this.deviceSelect.value,
            target_classes: this.getSelectedClasses(),
            frame_skip: parseInt(this.frameSkipSlider.value),
            line_y_ratio: parseFloat(this.lineYSlider.value),
            mid_x_ratio: parseFloat(this.midXSlider.value),
            swap_directions: this.swapDirToggle.checked
        };
        this.ws.send(JSON.stringify({ action: "update_config", config: config }));
    }

    updateButtonStates(running, paused) {
        this.startBtn.disabled = running;
        this.pauseBtn.disabled = !running;
        this.stopBtn.disabled = !running;
        this.pauseBtn.textContent = paused ? "▶️ Resume" : "⏸️ Pause";
    }

    renderSummaryTable(summaryData) {
        this.summaryTableBody.innerHTML = "";
        summaryData.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${row.time}</strong></td>
                <td>${row.avg_vehicles}</td>
                <td>${row.traffic_level}</td>
                <td>${row.inbound_flow}</td>
                <td>${row.outbound_flow}</td>
            `;
            this.summaryTableBody.appendChild(tr);
        });
    }

    downloadCSV() {
        if (!this.summaryEvents || this.summaryEvents.length === 0) {
            alert("No events data available to download.");
            return;
        }

        const headers = ["Timestamp (s)", "Real-world Time", "Vehicle ID", "Type", "Direction", "Traffic Level"];
        const rows = this.summaryEvents.map(e => [
            e["Timestamp (s)"],
            `"${e["Real-world Time"]}"`,
            e["Vehicle ID"],
            e["Type"],
            e["Direction"],
            `"${e["Traffic Level"]}"`
        ]);

        const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "KU_SRC_traffic_websocket_report.csv";
        a.click();
        URL.revokeObjectURL(url);
    }

    // ==========================================
    // Database & History (phpMyAdmin / MySQL)
    // ==========================================
    async checkDatabaseStatus() {
        try {
            const res = await fetch("/api/db/status");
            const data = await res.json();
            
            if (data.db_type && data.db_type.includes("MySQL")) {
                this.dbStatusBadge.className = "db-status";
                this.dbStatusText.textContent = `🟢 MySQL (phpMyAdmin)`;
                this.dbInfoSubtitle.textContent = `Database: ${data.database} | Host: ${data.host}:${data.port} | User: ${data.user}`;
            } else {
                this.dbStatusBadge.className = "db-status fallback";
                this.dbStatusText.textContent = `🟡 ${data.db_type || 'Local DB'}`;
                this.dbInfoSubtitle.textContent = `Storage: Local SQLite | MySQL Offline (Start MySQL in XAMPP / phpMyAdmin)`;
            }
        } catch (err) {
            this.dbStatusBadge.className = "db-status offline";
            this.dbStatusText.textContent = `🔴 DB Offline`;
            console.error("DB Status check failed:", err);
        }
    }

    openHistoryModal() {
        this.historyModal.style.display = "flex";
        this.checkDatabaseStatus();
        this.loadHistoryRecords();
    }

    closeHistoryModal() {
        this.historyModal.style.display = "none";
        this.sessionDetailContainer.style.display = "none";
    }

    async loadHistoryRecords() {
        this.historyTableBody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 2rem;">กำลังดึงข้อมูลประวัติจากฐานข้อมูล...</td></tr>`;
        try {
            const res = await fetch("/api/db/sessions?limit=50");
            const data = await res.json();
            this.cachedSessions = data.sessions || [];
            this.renderHistoryTable(this.cachedSessions);
        } catch (err) {
            this.historyTableBody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:#ef4444; padding: 2rem;">เกิดข้อผิดพลาดในการโหลดข้อมูล: ${err.message}</td></tr>`;
        }
    }

    renderHistoryTable(sessions) {
        if (!sessions || sessions.length === 0) {
            this.historyTableBody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 2rem; color:var(--text-muted);">ยังไม่มีประวัติการวิเคราะห์ที่บันทึกไว้</td></tr>`;
            return;
        }

        this.historyTableBody.innerHTML = "";
        sessions.forEach(s => {
            const tr = document.createElement("tr");
            tr.dataset.video = (s.video_name || "").toLowerCase();
            tr.dataset.congestion = (s.max_congestion_level || "").toLowerCase();

            let congBadgeClass = "badge-smooth";
            if (s.max_congestion_level && s.max_congestion_level.includes("หนาแน่นมาก")) congBadgeClass = "badge-jam";
            else if (s.max_congestion_level && s.max_congestion_level.includes("ปานกลาง")) congBadgeClass = "badge-moderate";
            else if (s.max_congestion_level && s.max_congestion_level.includes("ชะลอตัว")) congBadgeClass = "badge-slow";

            tr.innerHTML = `
                <td><strong>#${s.id}</strong></td>
                <td><code>${s.video_name}</code></td>
                <td>${s.video_recorded_time || '-'}</td>
                <td><strong style="color:var(--accent-blue);">${s.total_vehicles}</strong></td>
                <td>🔵 ${s.inbound_count}</td>
                <td>🟠 ${s.outbound_count}</td>
                <td><span class="badge ${congBadgeClass}">${s.max_congestion_level || 'คล่องตัว'}</span></td>
                <td>${s.analysis_timestamp || '-'}</td>
                <td>
                    <div class="action-btn-group">
                        <button class="btn-action-view" onclick="window.app.viewSessionDetail(${s.id})">🔍 ดูข้อมูล</button>
                        <button class="btn-action-delete" onclick="window.app.deleteSession(${s.id})">🗑️ ลบ</button>
                    </div>
                </td>
            `;
            this.historyTableBody.appendChild(tr);
        });
    }

    filterHistoryTable(query) {
        const rows = this.historyTableBody.querySelectorAll("tr");
        rows.forEach(row => {
            const video = row.dataset.video || "";
            const cong = row.dataset.congestion || "";
            if (!query || video.includes(query) || cong.includes(query)) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    }

    async viewSessionDetail(sessionId) {
        try {
            const res = await fetch(`/api/db/sessions/${sessionId}`);
            if (!res.ok) throw new Error("Could not fetch session details");
            const data = await res.json();

            this.detailTitle.textContent = `📊 รายละเอียดการวิเคราะห์ Session #${data.id} - ${data.video_name}`;
            
            this.detailMetaGrid.innerHTML = `
                <div class="meta-item">
                    <div class="meta-item-label">เวลาที่ถ่ายคลิป</div>
                    <div class="meta-item-val">${data.video_recorded_time || '-'}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-item-label">ยอดรถรวม</div>
                    <div class="meta-item-val" style="color:var(--accent-blue);">${data.total_vehicles} คัน</div>
                </div>
                <div class="meta-item">
                    <div class="meta-item-label">ขาเข้า / ขาออก</div>
                    <div class="meta-item-val">🔵 ${data.inbound_count} / 🟠 ${data.outbound_count}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-item-label">ทิศทางหลัก</div>
                    <div class="meta-item-val">${data.dominant_direction}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-item-label">โมเดลที่ใช้</div>
                    <div class="meta-item-val"><code>${data.model_used}</code></div>
                </div>
                <div class="meta-item">
                    <div class="meta-item-label">จำแนกประเภทยานพาหนะ</div>
                    <div class="meta-item-val" style="font-size:0.8rem;">
                        🚗 Car: ${data.class_counts?.Car || 0} | 🏍️ Moto: ${data.class_counts?.Motorcycle || 0}<br>
                        🚌 Bus: ${data.class_counts?.Bus || 0} | 🚚 Truck: ${data.class_counts?.Truck || 0}
                    </div>
                </div>
            `;

            this.detailIntervalsBody.innerHTML = "";
            if (data.intervals && data.intervals.length > 0) {
                data.intervals.forEach(intv => {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td><strong>${intv.time_window}</strong></td>
                        <td>${intv.inbound}</td>
                        <td>${intv.outbound}</td>
                        <td>${intv.total}</td>
                        <td>${(intv.stall_ratio * 100).toFixed(0)}%</td>
                        <td>${intv.congestion_level}</td>
                    `;
                    this.detailIntervalsBody.appendChild(row);
                });
            } else {
                this.detailIntervalsBody.innerHTML = `<tr><td colspan="6" style="text-align:center;">ไม่มีข้อมูล Interval</td></tr>`;
            }

            this.sessionDetailContainer.style.display = "block";
            this.sessionDetailContainer.scrollIntoView({ behavior: "smooth" });
        } catch (err) {
            alert(`ไม่สามารถโหลดรายละเอียด session: ${err.message}`);
        }
    }

    async deleteSession(sessionId) {
        if (!confirm(`คุณแน่ใจหรือไม่ว่าต้องการลบข้อมูลการวิเคราะห์ Session #${sessionId} จากฐานข้อมูล?`)) {
            return;
        }

        try {
            const res = await fetch(`/api/db/sessions/${sessionId}`, { method: "DELETE" });
            if (res.ok) {
                if (this.sessionDetailContainer.style.display !== "none") {
                    this.sessionDetailContainer.style.display = "none";
                }
                this.loadHistoryRecords();
            } else {
                alert("ไม่สามารถลบข้อมูลได้");
            }
        } catch (err) {
            alert(`เกิดข้อผิดพลาดในการลบ: ${err.message}`);
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    window.app = new TrafficWebSocketApp();
});
