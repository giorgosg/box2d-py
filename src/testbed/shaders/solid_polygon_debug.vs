// Simplified debug shader for solid polygon (no loop)
#version 330

uniform mat4 projectionMatrix;
uniform float pixelScale;

layout(location = 0) in vec2 v_localPosition;
layout(location = 1) in vec4 v_instanceTransform;
layout(location = 2) in vec4 v_instancePoints12; // unused now
layout(location = 6) in int v_instanceCount;       // unused now
layout(location = 7) in float v_instanceRadius;
layout(location = 8) in vec4 v_instanceColor;

out vec4 f_color;
out float f_thickness;

void main()
{
    // For debugging: ignore polygon points, use a fixed scale and center.
    float scale = v_instanceRadius + 0.5;  // constant scale
    vec2 center = vec2(0.0, 0.0);
    
    // Transform vertex:
    vec2 pos = scale * v_localPosition + center;
    float c = v_instanceTransform.z;
    float s = v_instanceTransform.w;
    // Apply rotation and translation from instanceTransform.xy as offset:
    vec2 transformed = vec2(c * pos.x - s * pos.y, s * pos.x + c * pos.y) + v_instanceTransform.xy;
    
    gl_Position = projectionMatrix * vec4(transformed, 0.0, 1.0);
    f_color = v_instanceColor;
    // Use a constant thickness for debugging
    f_thickness = 3.0;
}
