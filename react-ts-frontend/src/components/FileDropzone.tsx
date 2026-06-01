import React, { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Box, Typography, Paper } from "@mui/material";

interface Props {
    onFilesSelected: (files: File[]) => void;
}

const FileDropzone: React.FC<Props> = ({ onFilesSelected }) => {
    const onDrop = useCallback(
        (acceptedFiles: File[]) => {
            onFilesSelected(acceptedFiles);
        },
        [onFilesSelected]
    );

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { "image/*": [] },
    });

    return (
        <Paper
            {...getRootProps()}
            sx={{
                p: 3,
                textAlign: "center",
                border: "2px dashed #1976d2",
                cursor: "pointer",
            }}
        >
            <input {...getInputProps()} />
            {isDragActive ? (
                <Typography>Drop the files here ...</Typography>
            ) : (
                <Typography>Drag & drop some images here, or click to select files</Typography>
            )}
        </Paper>
    );
};

export default FileDropzone;
