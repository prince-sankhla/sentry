declare module "react-simple-maps" {
  import type { ComponentType, ReactNode, SVGProps } from "react";

  export interface GeographyShape {
    rsmKey: string;
    properties: Record<string, string>;
    geometry: unknown;
  }

  export const ComposableMap: ComponentType<{
    projection?: string;
    projectionConfig?: { scale?: number; center?: [number, number]; rotate?: [number, number, number] };
    width?: number;
    height?: number;
    style?: React.CSSProperties;
    children?: ReactNode;
  }>;

  export const ZoomableGroup: ComponentType<{
    zoom?: number;
    center?: [number, number];
    minZoom?: number;
    maxZoom?: number;
    onMoveEnd?: (position: { coordinates: [number, number]; zoom: number }) => void;
    children?: ReactNode;
  }>;

  export const Geographies: ComponentType<{
    geography: string | object;
    children: (args: { geographies: GeographyShape[] }) => ReactNode;
  }>;

  export const Geography: ComponentType<
    {
      geography: GeographyShape;
      style?: {
        default?: React.CSSProperties;
        hover?: React.CSSProperties;
        pressed?: React.CSSProperties;
      };
    } & Omit<SVGProps<SVGPathElement>, "style">
  >;

  export const Marker: ComponentType<{
    coordinates: [number, number];
    children?: ReactNode;
  } & SVGProps<SVGGElement>>;
}
