import { expect, test } from "@playwright/test";
test("home renders", async ({page}) => { await page.goto("/"); await expect(page.getByRole("heading", {name:"Software Factory"})).toBeVisible(); });

