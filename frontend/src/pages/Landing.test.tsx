import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Landing from "@/pages/Landing";

describe("Landing page", () => {
  it("renders the hero, navigation and product headline", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Built for integrity agencies/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByText(/Intelligence that explains/i)).toBeInTheDocument();
  });

  it("includes the required sections via id anchors", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    );
    const required = [
      "top",
      "problem",
      "how-it-works",
      "signals",
      "priority",
      "workflow",
      "humans",
      "ai",
      "integrity",
      "faq",
      "cta",
    ];
    for (const id of required) {
      expect(document.getElementById(id)).not.toBeNull();
    }
  });

  it("renders the intro overlay on first visit", () => {
    window.sessionStorage.removeItem("verity.intro.seen");
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Landing />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("intro-overlay")).toBeInTheDocument();
  });

  it("uses explainable, non-stigmatising language", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    );
    const body = document.body.textContent ?? "";
    expect(body).toMatch(/never a verdict about an athlete/i);
    expect(body).toMatch(/an anomaly is a lead, not a statement about anyone/i);
    expect(body).not.toMatch(/probability of guilt/i);
    expect(body).not.toMatch(/guilty athlete/i);
  });
});