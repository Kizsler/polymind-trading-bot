import { NextRequest, NextResponse } from "next/server";

// Use CLOB API which accepts condition IDs directly
const CLOB_API_URL = "https://clob.polymarket.com";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  try {
    const response = await fetch(`${CLOB_API_URL}/markets/${id}`, {
      headers: {
        Accept: "application/json",
      },
      next: { revalidate: 300 }, // Cache for 5 minutes
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Market not found" },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      condition_id: data.condition_id || id,
      question: data.question || "Unknown Market",
      description: data.description || "",
      end_date: data.end_date_iso || null,
      resolution_date: data.end_date_iso || null,
      active: data.active ?? true,
      closed: data.closed ?? false,
    });
  } catch (error) {
    console.error("Failed to fetch market:", error);
    return NextResponse.json(
      { error: "Failed to fetch market data" },
      { status: 500 }
    );
  }
}
