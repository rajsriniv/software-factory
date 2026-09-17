package com.example;

import static org.assertj.core.api.Assertions.assertThat;
import org.junit.jupiter.api.Test;

class ApplicationTest {
    @Test void greetingIsStable() { assertThat(new Application.Greeting("hello").message()).isEqualTo("hello"); }
}

