import { defineConfig, devices } from "@playwright/test";
export default defineConfig({testDir:"./e2e",retries:1,use:{baseURL:process.env.BASE_URL || "http://127.0.0.1:4173",trace:"on-first-retry"},projects:[{name:"chromium",use:{...devices["Desktop Chrome"]}},{name:"firefox",use:{...devices["Desktop Firefox"]}},{name:"webkit",use:{...devices["Desktop Safari"]}}]});

