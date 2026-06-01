export interface AppraisalResponseDTO {
    appraisalId: number;
    priceMin: number;
    priceMax: number;
    adjustedPriceMin?: number;
    adjustedPriceMax?: number;
    totalRepairCost?: number;
    hasDamageAssessment: boolean;
    damages?: DamageDTO[];
}

export interface DamageDTO {
    carPart: string;
    damageType: string;
    severity: string;
    repairCost: number;
    confidence: number;
}
