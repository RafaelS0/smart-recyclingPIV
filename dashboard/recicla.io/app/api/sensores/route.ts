import { NextResponse } from "next/server";
import { prisma } from "../../../components/server/db";

export async function GET() {
  try {
    const dispositivos = await prisma.dispositivo.findMany({
      orderBy: { ultimaComunicacao: "desc" },
      select: { id: true, codigo: true, nome: true, tipo: true, status: true, ultimaComunicacao: true },
    });
    // considera online se comunicou nos últimos 2 minutos
    const agora = Date.now();
    const items = dispositivos.map((d) => ({
      ...d,
      online: d.ultimaComunicacao ? agora - new Date(d.ultimaComunicacao).getTime() < 2 * 60 * 1000 : false,
    }));
    return NextResponse.json({ items });
  } catch {
    return NextResponse.json({ items: [] });
  }
}
