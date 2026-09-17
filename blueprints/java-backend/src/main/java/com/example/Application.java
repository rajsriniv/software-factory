package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class Application {
    public static void main(String[] args) { SpringApplication.run(Application.class, args); }
    @GetMapping("/api/hello") public Greeting hello() { return new Greeting("hello"); }
    public record Greeting(String message) {}
}

