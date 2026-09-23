const API_BASE = window.location.origin.includes(':5173') 
  ? 'http://127.0.0.1:8000' 
  : window.location.origin;

// Cache & in-flight deduplication to eliminate repetitive HTTP API spam
let _videosCache = null;
let _videosInFlight = null;
let _modelsCache = null;
let _modelsInFlight = null;

export const api = {
  async getVideos(forceRefresh = false) {
    if (!forceRefresh && _videosCache) return _videosCache;
    if (_videosInFlight) return _videosInFlight;

    _videosInFlight = (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/videos`);
        const data = await res.json();
        _videosCache = data;
        return data;
      } catch (err) {
        _videosCache = null;
        throw err;
      } finally {
        _videosInFlight = null;
      }
    })();
    return _videosInFlight;
  },

  async getModels(forceRefresh = false) {
    if (!forceRefresh && _modelsCache) return _modelsCache;
    if (_modelsInFlight) return _modelsInFlight;

    _modelsInFlight = (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/models`);
        const data = await res.json();
        _modelsCache = data;
        return data;
      } catch (err) {
        _modelsCache = null;
        throw err;
      } finally {
        _modelsInFlight = null;
      }
    })();
    return _modelsInFlight;
  },

  async uploadVideo(file, onProgress) {
    _videosCache = null; // Invalidate cache so newly uploaded video is reflected immediately
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      body: formData,
    });
    return await res.json();
  },

  async getCalibrationPreview(videoPath, lineYRatio, midXRatio, swapDirections, signal = null) {
    const params = new URLSearchParams({
      video_path: videoPath,
      line_y_ratio: lineYRatio,
      mid_x_ratio: midXRatio,
      swap_directions: swapDirections,
    });
    const options = signal ? { signal } : {};
    const res = await fetch(`${API_BASE}/api/calibration/preview?${params.toString()}`, options);
    return await res.json();
  },

  getExportUrl(format = 'csv') {
    return `${API_BASE}/api/export?format=${format}`;
  },

  async getPeakHoursReport(date = null) {
    const url = date ? `${API_BASE}/api/reports/peak-hours?date=${date}` : `${API_BASE}/api/reports/peak-hours`;
    const res = await fetch(url);
    return await res.json();
  },

  async getHistoryReport({ date = null, vehicleType = 'All', direction = 'All', page = 1, limit = 50 } = {}) {
    const params = new URLSearchParams({
      page: String(page),
      limit: String(limit),
      vehicle_type: vehicleType,
      direction: direction
    });
    if (date) params.append('date', date);
    const res = await fetch(`${API_BASE}/api/reports/history?${params.toString()}`);
    return await res.json();
  },

  async getReportDates() {
    const res = await fetch(`${API_BASE}/api/reports/dates`);
    return await res.json();
  },

  getReportExportUrl(date = null) {
    return date ? `${API_BASE}/api/reports/export?date=${date}` : `${API_BASE}/api/reports/export`;
  },

  async getBenchmarkPresets() {
    const res = await fetch(`${API_BASE}/api/benchmark/presets`);
    return await res.json();
  },

  async runBenchmark({ video_source = 'IMG_1357.MOV', models = [], sample_frames = 10, conf_threshold = 0.18, img_size = 480 } = {}) {
    const res = await fetch(`${API_BASE}/api/benchmark/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_source,
        models,
        sample_frames,
        conf_threshold,
        img_size
      })
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'การทดสอบความแม่นยำล้มเหลว');
    }
    return await res.json();
  },

  // --- Auth & Users API ---
  async login(username_or_email, password) {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username_or_email, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'เข้าสู่ระบบไม่สำเร็จ');
    return data;
  },

  async register(userData) {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'สมัครสมาชิกไม่สำเร็จ');
    return data;
  },

  async getMe(token) {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.user;
  },

  async getDemoAccounts() {
    const res = await fetch(`${API_BASE}/api/auth/demo-accounts`);
    return await res.json();
  },

  // --- Business & Branch API ---
  async getBusinessDashboard(businessId = null, date = null) {
    const params = new URLSearchParams();
    if (businessId) params.append('business_id', businessId);
    if (date) params.append('date', date);
    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/business/dashboard${query}`);
    return await res.json();
  },

  async getBusinesses() {
    const res = await fetch(`${API_BASE}/api/business/companies`);
    return await res.json();
  },

  async createBusiness(businessData) {
    const res = await fetch(`${API_BASE}/api/business/companies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(businessData)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'บันทึกข้อมูลธุรกิจไม่สำเร็จ');
    return data;
  },

  async updateBusiness(businessId, businessData) {
    const res = await fetch(`${API_BASE}/api/business/companies/${businessId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(businessData)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'อัปเดตข้อมูลธุรกิจไม่สำเร็จ');
    return data;
  },

  async deleteBusiness(businessId) {
    const res = await fetch(`${API_BASE}/api/business/companies/${businessId}`, {
      method: 'DELETE'
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'ลบข้อมูลธุรกิจไม่สำเร็จ');
    return data;
  },

  async getBusinessCameras(businessId = null) {
    const url = businessId ? `${API_BASE}/api/business/cameras?business_id=${businessId}` : `${API_BASE}/api/business/cameras`;
    const res = await fetch(url);
    return await res.json();
  },

  async createBusinessCamera(cameraData) {
    const res = await fetch(`${API_BASE}/api/business/cameras`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cameraData)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'บันทึกกล้องไม่สำเร็จ');
    return data;
  },

  async deleteBusinessCamera(cameraId) {
    const res = await fetch(`${API_BASE}/api/business/cameras/${cameraId}`, {
      method: 'DELETE'
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'ลบกล้องไม่สำเร็จ');
    return data;
  }
};
