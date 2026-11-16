import { NextRequest, NextResponse } from "next/server";
import { prisma } from "../../../components/server/db";

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const page = Math.max(1, Number(searchParams.get("page") ?? 1));
  const limit = Math.min(100, Math.max(1, Number(searchParams.get("limit") ?? 50)));
  const skip = (page - 1) * limit;

  try {
    const [items, total] = await Promise.all([
      prisma.classificacao.findMany({
        orderBy: { timestamp: "desc" },
        skip,
        take: limit,
        include: { dispositivo: { select: { nome: true, codigo: true } }, lixeira: { select: { nome: true } } },
      }),
      prisma.classificacao.count(),
    ]);
    return NextResponse.json({ items, total, page, limit });
  } catch {
    return NextResponse.json({ items: [], total: 0, page, limit });
  }
}
