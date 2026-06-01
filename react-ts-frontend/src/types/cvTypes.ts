export interface CvAnalysisRequest {
    appraisalId: number;
    images: string[]; // base64
}

export interface CvAnalysisResponse {
    damages: DamageItem[];
    totalRepairCost: number;
}

export interface DamageItem {
    carPart: string;
    damageType: string;
    severity: string;
    repairCost: number;
    confidence: number;
}