import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./pages/AuthContext";
import SplashScreen from "./pages/SplashScreen";
import MainPage from "./pages/MainPage";
import Calendar from "./pages/Calendar";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Mypage from "./pages/Mypage";
import FindPassword from "./pages/FindPassword";
import FaqPage from "./pages/Faq";
import AboutPage from "./pages/About";
import SavingsDetail from "./pages/SavingsDetail";
import ReceiptUpload from "./pages/ReceiptUpload";
import EventsPage from "./pages/Events";
import BoardPage from "./pages/Board";
import ProgressPage from "./pages/Progress";

export default function App() {
  const [showSplash, setShowSplash] = useState(true);

  return (
    //  AuthProvider를 Router 바깥으로 이동
    <AuthProvider>
      <Router>
        {showSplash ? (
          <SplashScreen onFinish={() => setShowSplash(false)} />
        ) : (
          <Routes>
            <Route path="/" element={<MainPage />} />
            <Route path="/calendar" element={<Calendar />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/mypage" element={<Mypage />} />
            <Route path="/find-password" element={<FindPassword />} />
            <Route path="/faq" element={<FaqPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/savings-detail" element={<SavingsDetail />} />
            <Route path="/receipt-upload" element={<ReceiptUpload />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/board" element={<BoardPage />} />
            <Route path="/progress" element={<ProgressPage />} />
          </Routes>
        )}
      </Router>
    </AuthProvider>
  );
}
