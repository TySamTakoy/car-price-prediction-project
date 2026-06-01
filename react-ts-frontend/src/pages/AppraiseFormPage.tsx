import React, { useState } from "react";
import {
    Container,
    Typography,
    TextField,
    Button,
    MenuItem,
    Grid,
    Box,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { appraiseCar } from "../api/appraisalApi";
import { CarRequestDTO } from "../types/carTypes";
import { BodyType, DriveType, EngineType, Transmission, Condition } from "../types/enums";

const AppraiseFormPage = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState<CarRequestDTO>({
        brand: "",
        model: "",
        generation: "",
        year: 2020,
        mileage: 0,
        engineVolume: 1.6,
        enginePower: 100,
        engineType: EngineType.PETROL,
        transmission: Transmission.MANUAL,
        driveType: DriveType.FWD,
        bodyType: BodyType.SEDAN,
        color: "",
        condition: Condition.EXCELLENT,
        ownersCount: 1,
        complectation: "",
    });

    const handleChange = (field: keyof CarRequestDTO, value: any) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmit = async () => {
        try {
            const response = await appraiseCar(formData);
            navigate(`/appraise/result/${response.appraisalId}`, { state: { response } });
        } catch (err) {
            console.error(err);
            alert("Error during appraisal");
        }
    };

    return (
        <Container sx={{ mt: 5 }}>
            <Typography variant="h4" gutterBottom>
                Car Appraisal Form
            </Typography>
            <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                    <TextField
                        label="Brand"
                        fullWidth
                        value={formData.brand}
                        onChange={e => handleChange("brand", e.target.value)}
                    />
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        label="Model"
                        fullWidth
                        value={formData.model}
                        onChange={e => handleChange("model", e.target.value)}
                    />
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        label="Year"
                        type="number"
                        fullWidth
                        value={formData.year}
                        onChange={e => handleChange("year", Number(e.target.value))}
                    />
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        label="Mileage"
                        type="number"
                        fullWidth
                        value={formData.mileage}
                        onChange={e => handleChange("mileage", Number(e.target.value))}
                    />
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        label="Engine Volume"
                        type="number"
                        fullWidth
                        value={formData.engineVolume}
                        onChange={e => handleChange("engineVolume", Number(e.target.value))}
                    />
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        label="Engine Power"
                        type="number"
                        fullWidth
                        value={formData.enginePower}
                        onChange={e => handleChange("enginePower", Number(e.target.value))}
                    />
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        select
                        label="Engine Type"
                        fullWidth
                        value={formData.engineType}
                        onChange={e => handleChange("engineType", e.target.value)}
                    >
                        {Object.values(EngineType).map(type => (
                            <MenuItem key={type} value={type}>{type}</MenuItem>
                        ))}
                    </TextField>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        select
                        label="Transmission"
                        fullWidth
                        value={formData.transmission}
                        onChange={e => handleChange("transmission", e.target.value)}
                    >
                        {Object.values(Transmission).map(type => (
                            <MenuItem key={type} value={type}>{type}</MenuItem>
                        ))}
                    </TextField>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        select
                        label="Drive Type"
                        fullWidth
                        value={formData.driveType}
                        onChange={e => handleChange("driveType", e.target.value)}
                    >
                        {Object.values(DriveType).map(type => (
                            <MenuItem key={type} value={type}>{type}</MenuItem>
                        ))}
                    </TextField>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        select
                        label="Body Type"
                        fullWidth
                        value={formData.bodyType}
                        onChange={e => handleChange("bodyType", e.target.value)}
                    >
                        {Object.values(BodyType).map(type => (
                            <MenuItem key={type} value={type}>{type}</MenuItem>
                        ))}
                    </TextField>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        label="Color"
                        fullWidth
                        value={formData.color}
                        onChange={e => handleChange("color", e.target.value)}
                    />
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        select
                        label="Condition"
                        fullWidth
                        value={formData.condition}
                        onChange={e => handleChange("condition", e.target.value)}
                    >
                        {Object.values(Condition).map(type => (
                            <MenuItem key={type} value={type}>{type}</MenuItem>
                        ))}
                    </TextField>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <TextField
                        label="Owners Count"
                        type="number"
                        fullWidth
                        value={formData.ownersCount}
                        onChange={e => handleChange("ownersCount", Number(e.target.value))}
                    />
                </Grid>
                <Grid item xs={12}>
                    <TextField
                        label="Complectation"
                        fullWidth
                        value={formData.complectation}
                        onChange={e => handleChange("complectation", e.target.value)}
                    />
                </Grid>
            </Grid>
            <Box sx={{ mt: 3 }}>
                <Button variant="contained" color="primary" onClick={handleSubmit}>
                    Calculate Appraisal
                </Button>
            </Box>
        </Container>
    );
};

export default AppraiseFormPage;
