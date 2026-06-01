import React from "react";
import { Container, Typography, Button, Box } from "@mui/material";
import { useNavigate } from "react-router-dom";

const HomePage = () => {
    const navigate = useNavigate();

    return (
        <Container sx={{ mt: 5 }}>
            <Typography variant="h3" gutterBottom>
                Car Price Prediction
            </Typography>
            <Box sx={{ mt: 3, display: "flex", gap: 2 }}>
                <Button
                    variant="contained"
                    color="primary"
                    onClick={() => navigate("/appraise")}
                >
                    Appraise Car
                </Button>
            </Box>
        </Container>
    );
};

export default HomePage;