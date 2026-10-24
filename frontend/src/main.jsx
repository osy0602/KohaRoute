import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CssBaseline } from "@mui/material";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import BookPickup from "./pages/BookPickup";
import TrackBooking from "./pages/TrackBooking";
import { staffRoutes } from "./routes/staffRoutes";

function App() {
    return (
        <AuthProvider>
            <Routes>
                <Route path="/" element={<Navigate to="/book" replace />} />
                <Route path="/book" element={<BookPickup />} />
                <Route path="/track" element={<TrackBooking />} />
                {staffRoutes}
                <Route path="*" element={<Navigate to="/book" replace />} />
            </Routes>
        </AuthProvider>
    );
}

createRoot(document.getElementById("root")).render(
    <StrictMode>
        <CssBaseline />
        <BrowserRouter>
            <App />
        </BrowserRouter>
    </StrictMode>,
);