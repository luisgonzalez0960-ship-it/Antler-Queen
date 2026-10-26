
import tkinter as tk
from tkinter import messagebox

ventana = tk.Tk()
ventana.geometry("400x100")
ventana.title("Cuadros de mensaje")

#messagebox.showinfo("Informacion", "Mensaje informativo")

#messagebox.showerror("ERROR", "Todo va a EXPLOTAR!!!!")

#messagebox.showwarning("Alerta", "Atento casi explota")

#respuesta = messagebox.askyesno("Confirmacion", "¿Acepta Continuar?")
#print(respuesta)
#if respuesta:
#    etiqueta = tk.Label(ventana, text="Aceptaste tu destino").pack()
#else:
#    etiqueta = tk.Label(ventana, text="No te nieges a tu destino").pack()

respuesta=messagebox.askquestion("Aceptas", "vas a reportar la materia")
print(respuesta)

respuesta=messagebox.askyesnocancel("Aceptas", "vas a reprobar la materia")
print(respuesta)

ventana.mainloop()