import React from "react";
import AppRouter from "./router/AppRouter";
import Navbar from "./components/Navbar";

function App() {
    return (
        <>
            <Navbar />
            <AppRouter />
        </>
    );
}

export default App;