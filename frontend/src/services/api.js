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

  async getCalibrationPreview(videoPath, lineYRatio, midXRatio, swapDirections) {
    const params = new URLSearchParams({
      video_path: videoPath,
      line_y_ratio: lineYRatio,
      mid_x_ratio: midXRatio,
      swap_directions: swapDirections,
    });
    const res = await fetch(`${API_BASE}/api/calibration/preview?${params.toString()}`);
    return await res.json();
  },

  getExportUrl(format = 'csv') {
    return `${API_BASE}/api/export?format=${format}`;
  }
};
