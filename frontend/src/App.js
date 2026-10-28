// src/App.js
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import HeadSchedule from './components/HeadSchedule';
import MatronSchedule from './components/MatronSchedule';
import SupervisorSchedule from './components/SupervisorSchedule';
import AISchedulePage from './components/AISchedulePage';
import ReportsPage from './components/ReportsPage';
import ExcelImportPage from './components/ExcelImportPage';

import TutorialPage from './components/TutorialPage';


function App() {
    const token = localStorage.getItem('access_token');

    return (
        <BrowserRouter 
            future={{ 
                v7_relativeSplatPath: true,
                v7_startTransition: true 
            }}
        >
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/dashboard" element={token ? <Dashboard /> : <Navigate to="/login" />} />
                <Route path="/head-schedule" element={token ? <HeadSchedule /> : <Navigate to="/login" />} />
                <Route path="/matron-schedule" element={token ? <MatronSchedule /> : <Navigate to="/login" />} />
                <Route path="/supervisor-schedule" element={token ? <SupervisorSchedule /> : <Navigate to="/login" />} />
                <Route path="/ai-schedule" element={token ? <AISchedulePage /> : <Navigate to="/login" />} />
                <Route path="/reports" element={token ? <ReportsPage /> : <Navigate to="/login" />} />
                <Route path="/" element={<Navigate to="/login" />} />
                <Route path="/excel-import" element={token ? <ExcelImportPage /> : <Navigate to="/login" />} />
            
                <Route path="/tutorial" element={<TutorialPage />} />

            </Routes>
        </BrowserRouter>
    );
}

export default App;