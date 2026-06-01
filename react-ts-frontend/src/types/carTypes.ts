import { BodyType, Condition, DriveType, EngineType, Transmission } from "./enums";

export interface CarRequestDTO {
    brand: string;
    model: string;
    generation?: string;
    year: number;
    mileage: number;
    engineVolume: number;
    enginePower: number;
    engineType: EngineType;
    transmission: Transmission;
    driveType: DriveType;
    bodyType: BodyType;
    color: string;
    condition: Condition;
    ownersCount: number;
    complectation?: string;
}