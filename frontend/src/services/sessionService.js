import axiosInstance from "../api/axiosInstance";

const sessionService = {
  getSessions: async () => {
    const resp = await axiosInstance.get("/sessions/");
    return resp.data;
  },

  revokeSession: async (id) => {
    const resp = await axiosInstance.post(`/sessions/${id}/revoke/`);
    return resp.data;
  },

  revokeOthers: async () => {
    const resp = await axiosInstance.post("/sessions/revoke-others/");
    return resp.data;
  },

  getSecurityEvents: async () => {
    const resp = await axiosInstance.get("/security-events/");
    return resp.data;
  },
};

export default sessionService;
