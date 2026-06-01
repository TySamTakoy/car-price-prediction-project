import React from "react";
import { Container, Typography, Box, Button, Card, CardContent } from "@mui/material";
import { useLocation, useNavigate } from "react-router-dom";

const AppraiseResultPage = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const response = location.state?.response;

    if (!response) {
        return <Typography>Appraisal not found</Typography>;
    }

    return (
        <Container sx={{ mt: 5 }}>
            <Typography variant="h4" gutterBottom>
                Car Appraisal Result
            </Typography>
            <Card sx={{ mt: 2 }}>
                <CardContent>
                    <Typography>Price Min: {response.priceMin}</Typography>
                    <Typography>Price Max: {response.priceMax}</Typography>
                    {response.adjustedPriceMin && (
                        <Typography>Adjusted Price Min: {response.adjustedPriceMin}</Typography>
                    )}
                    {response.adjustedPriceMax && (
                        <Typography>Adjusted Price Max: {response.adjustedPriceMax}</Typography>
                    )}
                    {response.hasDamageAssessment && (
                        <Typography>Total Repair Cost: {response.totalRepairCost}</Typography>
                    )}
                </CardContent>
            </Card>
            <Box sx={{ mt: 3 }}>
                <Button
                    variant="contained"
                    onClick={() => navigate(`/damage/${response.appraisalId}`)}
                >
                    Analyze Damage
                </Button>
            </Box>
        </Container>
    );
};

export default AppraiseResultPage;