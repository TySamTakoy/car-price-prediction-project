import { Routes, Route } from "react-router-dom";
import HomePage from "../pages/HomePage";
import AppraiseFormPage from "../pages/AppraiseFormPage";
import AppraiseResultPage from "../pages/AppraiseResultPage";
import DamageAnalysisPage from "../pages/DamageAnalysisPage";

export default function AppRouter() {
    return (
        <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/appraise" element={<AppraiseFormPage />} />
            <Route path="/appraise/result/:id" element={<AppraiseResultPage />} />
            <Route path="/damage/:id" element={<DamageAnalysisPage />} />
        </Routes>
    );
}
