import axiosInstance from "./axiosInstance";
import { CarRequestDTO } from "../types/carTypes";

// GET /api/cars/{id}
export const getCarById = async (id: number): Promise<CarRequestDTO> => {
    const { data } = await axiosInstance.get<CarRequestDTO>(`/cars/${id}`);
    return data;
};