import { NextResponse } from "next/server";

export async function GET() {
  try {
    const res = await fetch(
      "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true",
      {
        headers: { "Accept": "application/json" },
        next: { revalidate: 60 }, // Cache for 60 seconds
      }
    );

    if (!res.ok) {
      throw new Error(`CoinGecko API error: ${res.status}`);
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch crypto prices:", error);
    // Return fallback data
    return NextResponse.json({
      bitcoin: { usd: 0, usd_24h_change: 0 },
      ethereum: { usd: 0, usd_24h_change: 0 },
      solana: { usd: 0, usd_24h_change: 0 },
    });
  }
}
