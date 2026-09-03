const API_BASE = window.location.origin.includes(':5173') 
  ? 'http://localhost:8000' 
  : window.location.origin;

export const api = {
  async getVideos() {
    const res = await fetch(`${API_BASE}/api/videos`);
    return await res.json();
  },

  async getModels() {
    const res = await fetch(`${API_BASE}/api/models`);
    return await res.json();
  },

  async uploadVideo(file, onProgress) {
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
  }
};
