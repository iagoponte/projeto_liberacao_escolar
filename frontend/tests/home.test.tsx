import { describe, expect, it, vi } from "vitest";
import { redirect } from "next/navigation";
import HomePage from "../src/app/page";

vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
}));

describe("Página inicial", () => {
  it("redireciona para o login", () => {
    HomePage();

    expect(redirect).toHaveBeenCalledWith("/login");
  });
});