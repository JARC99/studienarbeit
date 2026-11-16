%--------------------------------------------------------------------------
%Perform Grid Convergence Study acc. to TFD-QSH
%Written by F. Herbst @ 29 August 2012
%Last Modification by S. Hohenstein @ 20 December 2012
%--------------------------------------------------------------------------
clear all
close all
%--------------------------------------------------
%Input Area
%--------------------------------------------------
 
fc3 = 91.2826385; % 0.70 mm
fc2 = 91.2810745; % 0.50 mm
fc1 = 91.2642136; % 0.30 mm
% fc1 = 91.2797928; % 0.15 mm


%Number of Grid Nodes 
N3 = 4251; % 0.70 mm
N2 = 10610; % 0.50 mm
N1 = 44633; % 0.30 mm
% N1 = 331072; % 0.15 mm

%Dimension of Simulation/Grid Refinement (Type for: 1D = 1; 2D = 2; 3D = 3)
D = 3;

%Safety Factor
Fs = 1.25;


%--------------------------------------------------
%--------------------------------------------------
%Don't Change Below
%--------------------------------------------------
disp '%--------------------------------------------------';
disp '%--------------------------------------------------';
disp '%Start new GCI Calculation...';
disp '%--------------------------------------------------';

%Check Validity of Input Data
%--------------------------------------------------
if ((fc1 > fc2) && (fc2 < fc3))
    error('Error: fci not monoton! Check your input, repeat your grid convergence study, or contact your CFD-expert')
end;

if ((fc1 < fc2) && (fc2 > fc3))
    error ('Error: fci not monoton! Check your input, repeat your grid convergence study, ounr contact your CFD-expert')
end;

if ((fc1 == fc2) | (fc2 == fc3))
    error ('Error: fci not monoton! Check your input, repeat your grid convergence study, or contact your CFD-expert')
end;

if ((N1 <= N2) | (N2 <= N3))
    error ('Error: Number of Grid Nodes illogical! Check your input!')
end;


disp 'Input Data Valid!';
disp '%--------------------------------------------------';

%--------------------------------------------------
%Calculation
%--------------------------------------------------
%Make Variables Global for pEq-Function
global epsilon32;
global epsilon21;
global r21;
global r32;
global s;

r21 = (N1/N2)^(1/D);
r32 = (N2/N3)^(1/D);

epsilon32 = (fc3-fc2);
epsilon21 = (fc2-fc1);

s = 1* sign(epsilon32/epsilon21);

x0 = log(epsilon32/epsilon21)/log(r21);
[p,resnorm]=lsqnonlin(@pEq,x0);

%--------------------------------------------------
%Calculation wih Actual p

%Calculate GCIs 
GCI_1 = Fs * abs((epsilon21/fc1))*1/((r21^p)-1);
GCI_2 = Fs * abs((epsilon32/fc2))*1/((r32^p)-1);
GCI_3 = GCI_2 * r32^p;

%Calculate Richardson extrapolated asymptotic Value
f_extra = fc1 + (fc1 - fc2)/((r21^p)-1);

%Calculate Estimated Extrapolated Relative Error
EERE_1 = abs((f_extra - fc1)/f_extra);
EERE_2 = abs((f_extra - fc2)/f_extra);
EERE_3 = abs((f_extra - fc3)/f_extra);

%Check Asymptotic Behaviour of Two Finest Grids
A_Flag=GCI_2/(GCI_1*(r21^p));

if ((A_Flag > 1.15 ) | (A_Flag < 0.85))
    error ('Error: Your fc-values are not in the asymptotic range! Refine your grid and repeat grid convergence study, or contact your CFD-expert')
end;


%--------------------------------------------------
%Calculation wih Conservative p = 1
%Calculate GCIs 
GCI_1_p1 = Fs * abs((epsilon21/fc1))*1/((r21)-1);
GCI_2_p1 = Fs * abs((epsilon32/fc2))*1/((r32)-1);
GCI_3_p1 = GCI_2_p1 * r32;

%Calculate Richardson extrapolated asymptotic Value
f_extra_p1 = fc1 + (fc1 - fc2)/((r21)-1);

%Calculate Estimated Extrapolated Relative Error
EERE_1_p1 = abs((f_extra_p1 - fc1)/f_extra_p1);
EERE_2_p1 = abs((f_extra_p1 - fc2)/f_extra_p1);
EERE_3_p1 = abs((f_extra_p1 - fc3)/f_extra_p1);

%--------------------------------------------------
%Output (Currently Under Construction)
disp('Input Values');
disp('--------------------------------------------------');
r21
r32
fc1
fc2
fc3
disp('Grid Convergence Study with Actual p');
disp('--------------------------------------------------');
p
f_extra
GCI_1
GCI_2
GCI_3
EERE_1
EERE_2
EERE_3
disp('Asymptotic Behaviour of Two Finest Grids (Value should be approx. 1)');
disp('--------------------------------------------------');
A_Flag
disp('Grid Convergence Study with Conservative p=1');
disp('--------------------------------------------------');
f_extra_p1
GCI_1_p1
GCI_2_p1
GCI_3_p1
EERE_1_p1
EERE_2_p1
EERE_3_p1

disp 'Congratulations - GCI calculation successfull!';
disp '--------------------------------------------------';
disp(newline)

%--------------------------------------------------
% Output as LaTeX Code
%--------------------------------------------------

disp('Copy the LaTeX code below into your document:');
disp('--------------------------------------------------');
% --- Combined Table: Inputs, GCI, and Error Analysis ---
fprintf('\\begin{table}[htbp]\n');
fprintf('\t\\centering\n');
fprintf('\t\\begin{tabular}{lc}\n');
fprintf('\t\t\\toprule\n');
fprintf('\t\tVariable & Wert \\\\\n');
fprintf('\t\t\\midrule\n');
fprintf('\t\t$r_{32}$ & %.4f \\\\\n', r32);
fprintf('\t\t$r_{21}$ & %.4f \\\\\n', r21);
fprintf('\t\t$f_{c, 1}$ & %.4f \\\\\n', fc1);
fprintf('\t\t$f_{c, 2}$ & %.4f \\\\\n', fc2);
fprintf('\t\t$f_{c, 3}$ & %.4f \\\\\n', fc3);
fprintf('\t\t$p$ & %.4f \\\\\n', p);
fprintf('\t\t$f_e$ & %.4f \\\\\n', f_extra);
fprintf('\t\t$F_s$ & %.2f \\\\\n', Fs);
fprintf('\t\t$GCI_1$ & %.2e \\\\\n', GCI_1);
fprintf('\t\t$GCI_2$ & %.2e \\\\\n', GCI_2);
fprintf('\t\t$GCI_3$ & %.2e \\\\\n', GCI_3);
fprintf('\t\t$GCI_2 / (GCI_1 r_{21}^p)$ & %.4f \\\\\n', A_Flag);
fprintf('\t\t$EERE_1$ & %.2e \\\\\n', EERE_1);
fprintf('\t\t$EERE_2$ & %.2e \\\\\n', EERE_2);
fprintf('\t\t$EERE_3$ & %.2e \\\\\n', EERE_3);
fprintf('\t\t\\midrule\n');
fprintf('\t\t$f_{e, p=1}$ & %.4f \\\\\n', f_extra_p1);
fprintf('\t\t$GCI_{1, p=1}$ & %.2e \\\\\n', GCI_1_p1);
fprintf('\t\t$GCI_{2, p=1}$ & %.2e \\\\\n', GCI_2_p1);
fprintf('\t\t$GCI_{3, p=1}$ & %.2e \\\\\n', GCI_3_p1);
fprintf('\t\t$EERE_{1, p=1}$ & %.2e \\\\\n', EERE_1_p1);
fprintf('\t\t$EERE_{2, p=1}$ & %.2e \\\\\n', EERE_2_p1);
fprintf('\t\t$EERE_{3, p=1}$ & %.2e \\\\\n', EERE_3_p1);
fprintf('\t\t\\bottomrule\n');
fprintf('\t\\end{tabular}\n');
fprintf('\t\\caption{Eingangsgrößen und Ergebnisse der Netzkonvergenzstudie [CITAR LEITFADEN AQUÍ].}\n');
fprintf('\\end{table}\n');