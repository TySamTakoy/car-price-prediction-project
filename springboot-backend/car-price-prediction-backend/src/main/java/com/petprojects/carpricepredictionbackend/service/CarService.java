package com.petprojects.carpricepredictionbackend.service;

import com.petprojects.carpricepredictionbackend.dto.CarRequestDTO;
import com.petprojects.carpricepredictionbackend.model.Car;
import com.petprojects.carpricepredictionbackend.repository.CarRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class CarService {

    private final CarRepository carRepository;

    @Transactional
    public Car saveCar(CarRequestDTO dto) {
        Car car = Car.builder()
                .brand(dto.getBrand())
                .model(dto.getModel())
                .generation(dto.getGeneration())
                .year(dto.getYear())
                .mileage(dto.getMileage())
                .engineVolume(dto.getEngineVolume())
                .enginePower(dto.getEnginePower())
                .engineType(dto.getEngineType())
                .transmission(dto.getTransmission())
                .driveType(dto.getDriveType())
                .bodyType(dto.getBodyType())
                .color(dto.getColor())
                .condition(dto.getCondition())
                .ownersCount(dto.getOwnersCount())
                .complectation(dto.getComplectation())
                .build();

        Car saved = carRepository.save(car);
        log.info("Saved car id={} ({} {})",
                saved.getId(), saved.getBrand(), saved.getModel());
        return saved;
    }

    @Transactional(readOnly = true)
    public CarRequestDTO findById(Long id) {
        Car car = carRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Car not found: " + id));
        return toDto(car);
    }

    private CarRequestDTO toDto(Car car) {
        CarRequestDTO dto = new CarRequestDTO();
        dto.setBrand(car.getBrand());
        dto.setModel(car.getModel());
        dto.setGeneration(car.getGeneration());
        dto.setYear(car.getYear());
        dto.setMileage(car.getMileage());
        dto.setEngineVolume(car.getEngineVolume());
        dto.setEnginePower(car.getEnginePower());
        dto.setEngineType(car.getEngineType());
        dto.setTransmission(car.getTransmission());
        dto.setDriveType(car.getDriveType());
        dto.setBodyType(car.getBodyType());
        dto.setColor(car.getColor());
        dto.setCondition(car.getCondition());
        dto.setOwnersCount(car.getOwnersCount());
        dto.setComplectation(car.getComplectation());
        return dto;
    }
}