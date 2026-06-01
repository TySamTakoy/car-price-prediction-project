import axiosInstance from "./axiosInstance";
import { CarRequestDTO } from "../types/carTypes";
import { CvAnalysisRequest } from "../types/cvTypes";
import { AppraisalResponseDTO } from "../types/appraisalTypes";

// POST /api/appraisal/car
export const appraiseCar = async (car: CarRequestDTO): Promise<AppraisalResponseDTO> => {
    const { data } = await axiosInstance.post<AppraisalResponseDTO>("/appraisal/car", car);
    return data;
};

// POST /api/appraisal/damage
export const analyzeDamage = async (request: CvAnalysisRequest): Promise<AppraisalResponseDTO> => {
    const { data } = await axiosInstance.post<AppraisalResponseDTO>("/appraisal/damage", request);
    return data;
};
