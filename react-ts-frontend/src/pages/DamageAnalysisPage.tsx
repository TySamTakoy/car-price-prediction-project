import React, { useState } from "react";
import { Container, Typography, Box, Button, Card, CardContent, Grid } from "@mui/material";
import { useParams } from "react-router-dom";
import FileDropzone from "../components/FileDropzone";
import { fileToBase64 } from "../utils/toBase64";
import { analyzeDamage } from "../api/appraisalApi";

const DamageAnalysisPage = () => {
    const { id } = useParams();
    const [files, setFiles] = useState<File[]>([]);
    const [result, setResult] = useState<any>(null);

    const handleFilesSelected = (selectedFiles: File[]) => {
        setFiles(selectedFiles);
    };

    const handleAnalyze = async () => {
        try {
            const base64Images = await Promise.all(files.map(file => fileToBase64(file)));
            const response = await analyzeDamage({ appraisalId: Number(id), images: base64Images });
            setResult(response);
        } catch (err) {
            console.error(err);
            alert("Error analyzing damage");
        }
    };

    return (
        <Container sx={{ mt: 5 }}>
            <Typography variant="h4" gutterBottom>
                Damage Analysis
            </Typography>
            <FileDropzone onFilesSelected={handleFilesSelected} />
            <Box sx={{ mt: 2 }}>
                <Button variant="contained" onClick={handleAnalyze} disabled={files.length === 0}>
                    Analyze
                </Button>
            </Box>
            {result && (
                <Box sx={{ mt: 3 }}>
                    <Typography variant="h5">Analysis Result</Typography>
                    <Typography>Total Repair Cost: {result.totalRepairCost}</Typography>
                    <Grid container spacing={2} sx={{ mt: 2 }}>
                        {result.damages.map((d: any, index: number) => (
                            <Grid item xs={12} sm={6} md={4} key={index}>
                                <Card>
                                    <CardContent>
                                        <Typography>Part: {d.carPart}</Typography>
                                        <Typography>Type: {d.damageType}</Typography>
                                        <Typography>Severity: {d.severity}</Typography>
                                        <Typography>Repair Cost: {d.repairCost}</Typography>
                                        <Typography>Confidence: {d.confidence}</Typography>
                                    </CardContent>
                                </Card>
                            </Grid>
                        ))}
                    </Grid>
                </Box>
            )}
        </Container>
    );
};

export default DamageAnalysisPage;